import time
import json
from datetime import datetime

from pydantic import BaseModel, Field
from typing import Literal

from app.ai.graph import graph
from app.ai.tools import edit_interaction
from app.ai.llm import llm


class MessageIntent(BaseModel):
    """
    Classifies whether the user's message describes a brand new HCP
    interaction happening, or is a correction/edit to something already
    logged (even a short one like a single field, or one with no name at
    all like "it was a phone call, not a visit").
    """
    intent: Literal["new_interaction", "correction"] = Field(
        description=(
            "new_interaction: the message describes a fresh visit, call, "
            "meeting, or conference that just happened, with enough detail "
            "to log as a new record, AND names the HCP involved. "
            "correction: the message is fixing, clarifying, or changing "
            "something about an interaction that was already logged — "
            "even if it names a doctor, even if it's very short, even if "
            "it doesn't use words like 'sorry' or 'actually', and almost "
            "always when no HCP name is mentioned at all. When in doubt "
            "between the two, prefer correction."
        )
    )


intent_classifier = llm.with_structured_output(MessageIntent)


def _classify_intent(message: str) -> str:
    prompt = f"""Classify this message from a sales rep talking to an AI CRM assistant.

Message: "{message}"

Decision rule: does this message describe an ACTION the rep took (visited,
called, met, had a call/meeting) with a NAMED HCP, plus what was discussed or
what happened? If yes, it's new_interaction — even if the tone is casual, even
if it includes the HCP's reaction or a follow-up detail. A new_interaction
message is a small STORY: who, what happened, what came of it.

Strong signal: if the message does NOT name an HCP, it is almost always a
correction — even if it describes a time, date, place, or event-sounding
detail. Reps only omit the name when they're amending something already on
record, since a brand-new interaction can't be logged without knowing who it
was with.

A correction message does NOT describe a new event happening — it's a short
fix, clarification, or amendment to something already logged. It typically
either has no action verb at all, or explicitly contradicts/replaces a detail
("not X, it was Y", "make it X instead", "her name is spelled X"), OR it
omits an HCP name entirely.

Examples of new_interaction (has an action verb + NAMED HCP + what happened):
- "Visited Dr. Sharma today, discussed Product X, positive feedback"
- "Had a call with Dr. Mehta about dosage guidelines"
- "Had a quick call with Dr. Verma about the trial results, she wants more data before committing"
- "Stopped by Dr. Nair's clinic this morning, walked her through the new dosing chart"

Examples of correction (no new action described, or no HCP named, just a fix to existing data):
- "it was a phone call, not a visit"
- "the name is Dr. Smith"
- "make the sentiment neutral"
- "change the date to yesterday"
- "that was over the phone, not in person"
- "make it next Tuesday instead"
- "It was closer to 4pm"
- "That actually happened on the 10th"

If the message names a doctor AND describes an action/event with that doctor,
always choose new_interaction, regardless of casual tone or included reactions.
If the message does NOT name a doctor, choose correction, even if it mentions
a time, date, or something that "happened."
"""
    result = intent_classifier.invoke(prompt)
    return result.intent


def _format_display_value(field: str, value):
    """Format a field's value for display in chat text only.
    Does not mutate the underlying stored value in `changes`."""
    if value == "":
        return "(none)"
    if field == "time" and isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).strftime("%I:%M %p").lstrip("0")
            except ValueError:
                continue
    return value


def _format_edit_response(changes: dict) -> str:
    if not changes or "error" in changes:
        return "Sorry, I couldn't find anything to update."

    parts = []
    for field, value in changes.items():
        if field == "hcp_name":
            continue
        label = field.replace("_", " ").title()
        display_value = _format_display_value(field, value)
        parts.append(f"{label}: {display_value}")

    hcp_name = changes.get("hcp_name")
    if hcp_name and not parts:
        return f"✅ Interaction updated! HCP name is now {hcp_name}."
    if hcp_name:
        return f"✅ Interaction updated! {hcp_name} — " + ", ".join(parts) + "."
    return "✅ Interaction updated! " + ", ".join(parts) + "."


def _invoke_with_retry(message: str, retries: int = 3):
    last_error = None
    for attempt in range(retries + 1):
        try:
            return graph.invoke({
                "messages": [{"role": "user", "content": message}]
            })
        except Exception as e:
            last_error = e
            err_str = str(e)
            if "tool_use_failed" in err_str or "Failed to call a function" in err_str:
                print(f"Attempt {attempt + 1} failed with malformed tool call, retrying...")
                continue
            raise
    raise last_error


def chat_with_agent(message: str):
    start = time.time()
    print("Calling graph...")
    print("User message:", message)

    intent = _classify_intent(message)
    print("Classified intent:", intent)

    if intent == "correction":
        print("-> calling edit_interaction directly")
        try:
            raw_result = edit_interaction.invoke({"correction": message})
            changes = json.loads(raw_result)
        except Exception as e:
            print("DIRECT EDIT ERROR:", str(e))
            return {"ai_response": "Sorry, I couldn't process that correction."}

        ai_text = _format_edit_response(changes)
        return {**changes, "ai_response": ai_text}

    try:
        response = _invoke_with_retry(message)
    except Exception as e:
        print("GRAPH ERROR:", str(e))
        return {"ai_response": "Sorry, something went wrong processing that."}

    print("========== GRAPH RESPONSE ==========")
    print(response)
    print("Graph completed in", time.time() - start, "seconds")

    tool_data = {}
    tool_was_called = False

    for msg in reversed(response["messages"]):
        if getattr(msg, "type", "") == "tool":
            tool_was_called = True
            try:
                tool_data = json.loads(msg.content)
            except Exception:
                pass
            break

    ai_text = response["messages"][-1].content
    if tool_was_called and not ai_text.strip():
        ai_text = "✅ Interaction logged successfully!"

    return {
        **tool_data,
        "ai_response": ai_text,
    }