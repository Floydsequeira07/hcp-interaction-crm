import time
import json
from datetime import datetime

from pydantic import BaseModel, Field
from typing import Literal

from app.ai.graph import graph
from app.ai.tools import edit_interaction, log_interaction
from app.ai.llm import llm


class MessageIntent(BaseModel):
    """
    Classifies whether the user's message describes a brand new HCP
    interaction happening, is a correction/edit to something already logged,
    or is neither (greeting, small talk, thanks, general question, history/
    summary/follow-up request, etc.) — the "other" category exists
    specifically so those messages are NOT forced into correction just
    because they don't describe a new interaction either.
    """
    intent: Literal["new_interaction", "correction", "other"] = Field(
        description=(
            "new_interaction: the message describes a fresh visit, call, "
            "meeting, or conference that just happened, with enough detail "
            "to log as a new record, AND names the HCP involved. "
            "correction: the message is fixing, clarifying, or changing "
            "something about an interaction that was already logged — "
            "even if it names a doctor, even if it's very short, even if "
            "it doesn't use words like 'sorry' or 'actually'. "
            "other: greetings ('hi', 'hello', 'good evening', 'thanks'), "
            "small talk, general questions, or requests to view "
            "history/summary/follow-up suggestions. Do NOT default a plain "
            "greeting or small talk to correction just because it has no "
            "HCP name and doesn't describe a new event — only choose "
            "correction if the message is actually amending existing data "
            "(a time, date, sentiment, name, etc. being fixed or changed)."
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

If the message does NOT name an HCP AND is actually amending/fixing a
previously logged detail (a time, date, sentiment, name, outcome, etc. being
corrected), it's correction — reps omit the name when they're clearly
continuing a correction to something already on record.

If the message is a greeting, small talk, thanks, a general question, or a
request to view history/summarize/get a follow-up suggestion, it is "other"
— NEVER correction. A short casual message with no correction content and no
new-event content (e.g. "hello", "good evening", "thanks", "how's it going")
is ALWAYS other. Do not default to correction just because it's short or has
no HCP name — "other" exists exactly for this case.

Examples of new_interaction (has an action verb + NAMED HCP + what happened):
- "Visited Dr. Sharma today, discussed Product X, positive feedback"
- "Had a call with Dr. Mehta about dosage guidelines"
- "Had a quick call with Dr. Verma about the trial results, she wants more data before committing"
- "Stopped by Dr. Nair's clinic this morning, walked her through the new dosing chart"

Examples of correction (no new action described, or no HCP named, but IS fixing existing data):
- "it was a phone call, not a visit"
- "the name is Dr. Smith"
- "make the sentiment neutral"
- "change the date to yesterday"
- "that was over the phone, not in person"
- "make it next Tuesday instead"
- "It was closer to 4pm"
- "That actually happened on the 10th"

Examples of other (neither correction nor new interaction — NOT amending anything):
- "hello"
- "good evening"
- "hi there"
- "thanks!"
- "how's it going"
- "show me Dr. Rao's history"
- "summarize my visits with Dr. Nair"
- "any follow-up suggestions for Dr. Verma?"

If the message names a doctor AND describes an action/event with that doctor,
always choose new_interaction, regardless of casual tone or included reactions.
If the message does NOT name a doctor, ask: is it actually correcting/fixing a
detail? If yes -> correction. If it's just a greeting/small talk/question with
nothing to fix -> other.
"""
    result = intent_classifier.invoke(prompt)
    return result.intent


def _format_display_value(field: str, value):
    """Format a field's value for display in chat text only.
    Does not mutate the underlying stored value in `changes`."""
    if value == "" or value is None:
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


def _format_log_response(data: dict) -> str:
    """Builds the '✅ Interaction logged successfully!' summary in Python,
    instead of relying on the agent's own text generation, since that part
    doesn't need an LLM call at all — the tool already returned everything
    needed."""
    label_map = [
        ("hcp_name", "HCP Name"),
        ("interaction_type", "Interaction Type"),
        ("date", "Date"),
        ("time", "Time"),
        ("attendees", "Attendees"),
        ("sentiment", "Sentiment"),
        ("materials_shared", "Materials Shared"),
        ("samples_distributed", "Samples Distributed"),
        ("outcomes", "Outcome"),
    ]

    parts = []
    for field, label in label_map:
        value = data.get(field)
        if value in (None, ""):
            continue
        display_value = _format_display_value(field, value)
        if field == "sentiment" and isinstance(display_value, str):
            display_value = display_value.capitalize()
        parts.append(f"{label}: {display_value}")

    summary = ", ".join(parts)
    return f"✅ Interaction logged successfully! {summary}. Would you like a follow-up suggestion?"


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

    # Both correction and new_interaction bypass the agent's own tool-calling
    # entirely and call the tool directly in code. Groq's function-calling
    # wire format has repeatedly produced malformed output for both of these
    # (especially at temperature=0, where a bad generation repeats
    # identically on every retry) — calling the tool directly removes that
    # unreliable layer completely for the two most important actions.
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

    if intent == "new_interaction":
        print("-> calling log_interaction directly")
        try:
            raw_result = log_interaction.invoke({"interaction": message})
            data = json.loads(raw_result)
        except Exception as e:
            print("DIRECT LOG ERROR:", str(e))
            return {"ai_response": "Sorry, I couldn't process that interaction."}

        ai_text = _format_log_response(data)
        return {**data, "ai_response": ai_text}

    # "other" (greetings, small talk, history/summary/follow-up requests)
    # still goes through the full agent, since it genuinely needs to choose
    # between multiple tools (or no tool at all) and write a natural reply.
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