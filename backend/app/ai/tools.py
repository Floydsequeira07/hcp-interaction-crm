from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
import json
import re
from datetime import datetime, timedelta

from app.ai.llm import llm

from app.database import SessionLocal
from app.crud import create_interaction, update_interaction, update_interaction_fields
from app.schemas import InteractionCreate
from app.models import HCPInteraction

import time


class InteractionCorrection(BaseModel):
    """
    Every field defaults to None (unset). Only fill in a field if the user's
    correction message explicitly changes it. Leaving a field as None means
    it will NOT be touched in the database — this is critical: do not guess,
    infer, or "helpfully" fill in fields the user did not mention.
    """
    hcp_name: Optional[str] = Field(default=None, description="Only set if the user is correcting the doctor's name")
    interaction_type: Optional[str] = Field(default=None, description="Only set if the user is correcting Visit/Call/Meeting/Conference")
    date: Optional[str] = Field(default=None, description="Only set if the user is correcting the date")
    time: Optional[str] = Field(default=None, description="Only set if the user is correcting the time")
    attendees: Optional[str] = Field(default=None, description="Only set if the user is correcting attendees")
    topics_discussed: Optional[str] = Field(default=None, description="Only set if the user is correcting the topics discussed")
    materials_shared: Optional[str] = Field(default=None, description="Only set if the user is correcting materials shared")
    samples_distributed: Optional[str] = Field(default=None, description="Only set if the user is correcting samples distributed")
    sentiment: Optional[str] = Field(default=None, description="Only set if the user is correcting the sentiment (Positive/Neutral/Negative)")
    outcomes: Optional[str] = Field(default=None, description="Only set if the user is correcting the outcome")
    follow_up_actions: Optional[str] = Field(default=None, description="Only set if the user is correcting the follow-up action")


correction_llm = llm.with_structured_output(InteractionCorrection)


def extract_json(raw: str) -> dict:
    """
    Strip markdown code fences (```json ... ``` or ``` ... ```) that models
    sometimes wrap JSON in, then parse it. Raises the original json error
    if the content still isn't valid JSON after stripping.
    """
    content = raw.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
        content = content.strip()
    return json.loads(content)


def resolve_relative_date(date_str: str):
    """
    Convert relative words like 'today', 'yesterday', 'tomorrow'
    or a proper YYYY-MM-DD string into a real date object.
    Returns None if it cannot be resolved (caller should fall back to now).
    """
    if not date_str:
        return None

    s = date_str.strip().lower()
    today = datetime.now().date()

    if s == "today":
        return today
    if s == "yesterday":
        return today - timedelta(days=1)
    if s == "tomorrow":
        return today + timedelta(days=1)

    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def resolve_time(time_str: str):
    """
    Convert free-text time like '3pm', '3:00 pm' or a proper
    HH:MM:SS string into a normalized 'HH:MM:SS' string.
    Returns None if it cannot be resolved (caller should fall back to now).
    """
    if not time_str:
        return None

    s = time_str.strip().lower()

    match = re.match(r"^(\d{1,2})(:(\d{2}))?\s*(am|pm)$", s)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(3) or 0)
        period = match.group(4)
        if period == "pm" and hour != 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}:00"

    try:
        datetime.strptime(time_str.strip(), "%H:%M:%S")
        return time_str.strip()
    except ValueError:
        pass

    try:
        parsed = datetime.strptime(time_str.strip(), "%H:%M")
        return parsed.strftime("%H:%M:%S")
    except ValueError:
        return None


@tool
def log_interaction(interaction: str):
    """
    Extract HCP interaction details and save them to MySQL.
    """

    db = SessionLocal()

    try:
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        prompt = f"""
You are an AI CRM assistant.

Today's actual date is {today_str}. Use this to correctly resolve relative
date words:
- "today" -> {today_str}
- "yesterday" -> the day before {today_str}
- "tomorrow" -> the day after {today_str}
Always return the resolved real date in YYYY-MM-DD format, never the word itself.

If the person mentions an explicit date or time (e.g. "March 5th", "at 2pm"),
use that instead of today's date/time.

Extract the HCP interaction into the JSON schema below.

Rules:
- Return ONLY valid JSON, no markdown code fences, no ```json, no explanation.
- Return every field exactly as shown.
- If a value is missing, return "".
- Return date in YYYY-MM-DD format (never a relative word like "today").
- Return time in HH:MM:SS (24-hour) format.
- interaction_type must be exactly one of: Visit, Call, Meeting, Conference (pick closest match); sentiment must be exactly one of: positive, neutral, negative.

Schema:
{{
    "hcp_name":"",
    "interaction_type":"Visit",
    "date":"",
    "time":"",
    "attendees":"",
    "topics_discussed":"",
    "materials_shared":"",
    "samples_distributed":"",
    "sentiment":"",
    "outcomes":"",
    "follow_up_actions":""
}}

Interaction:
{interaction}
"""

        print("========== log_interaction called ==========")

        start = time.time()
        print("1. Calling extraction LLM...")

        response = llm.invoke(prompt)

        print("2. LLM finished in", time.time() - start, "seconds")

        print("========== LLM RESPONSE ==========")
        print(response.content)
        print("==================================")

        data = extract_json(response.content)

        resolved_date = resolve_relative_date(data.get("date", ""))
        data["date"] = resolved_date if resolved_date else now.date()

        resolved_time = resolve_time(data.get("time", ""))
        data["time"] = resolved_time if resolved_time else now.time().replace(microsecond=0)

        print("3. JSON parsed")
        print(data)

        interaction_data = InteractionCreate(**data)

        print("4. Pydantic object created")

        create_interaction(db, interaction_data)

        print("5. Saved to MySQL")

        data["date"] = str(data["date"])
        data["time"] = str(data["time"])

        return json.dumps(data)

    except Exception as e:
        print("ERROR:", str(e))
        raise

    finally:
        db.close()


@tool
def edit_interaction(correction: str):
    """
    Correct or update fields of the most recently logged HCP interaction,
    based on a natural language correction (e.g. "the doctor name is Dr. Smith",
    "actually the sentiment was negative"). Do NOT pass an interaction_id or a
    pre-built data dict — just pass the user's correction text as a single string.
    """

    db = SessionLocal()

    try:
        last = (
            db.query(HCPInteraction)
            .order_by(HCPInteraction.id.desc())
            .first()
        )

        if not last:
            return json.dumps({"error": "No interaction found to edit."})

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        prompt = f"""
You are an AI CRM assistant correcting a previously logged interaction.

Today's actual date is {today_str}.

Current interaction values (for your reference only — do NOT copy these back
unless the user is explicitly changing that exact field):
hcp_name: {last.hcp_name}
interaction_type: {last.interaction_type}
date: {last.date}
time: {last.time}
attendees: {last.attendees}
topics_discussed: {last.topics_discussed}
materials_shared: {last.materials_shared}
samples_distributed: {last.samples_distributed}
sentiment: {last.sentiment}
outcomes: {last.outcomes}
follow_up_actions: {last.follow_up_actions}

The user's message below mentions changing ONE thing, or at most a couple of
things. Leave every field you output as null/unset EXCEPT the one(s) the user
is explicitly correcting. Do not touch sentiment, topics_discussed, outcomes,
or any other field unless the user's message is specifically about that field.

User correction:
{correction}
"""

        print("========== edit_interaction called ==========")

        start = time.time()
        print("1. Calling correction LLM (structured output)...")

        parsed = correction_llm.invoke(prompt)

        print("2. LLM finished in", time.time() - start, "seconds")
        print("========== STRUCTURED RESULT ==========")
        print(parsed)
        print("========================================")

        # Only keep fields the model actually set (not None) — this is the
        # real guarantee against the model touching unrelated fields, since
        # every field defaults to None unless explicitly filled in.
        changes = {k: v for k, v in parsed.model_dump().items() if v is not None}

        if "date" in changes:
            resolved_date = resolve_relative_date(changes.get("date", ""))
            if resolved_date:
                changes["date"] = resolved_date

        if "time" in changes:
            resolved_time = resolve_time(changes.get("time", ""))
            if resolved_time:
                changes["time"] = resolved_time

        print("3. Changes parsed:", changes)

        updated = update_interaction_fields(db, last.id, changes)

        if updated is None:
            return json.dumps({"error": "Interaction not found."})

        print("4. Updated in MySQL")

        # Only return what actually changed, plus hcp_name so the response
        # can still say whose record this is, without dumping every other
        # unchanged field back to the agent.
        result = {"hcp_name": updated.hcp_name}
        for field, value in changes.items():
            result[field] = str(value) if field in ("date", "time") else value

        print("Changed fields only:", result)

        return json.dumps(result)

    except Exception as e:
        print("ERROR:", str(e))
        raise

    finally:
        db.close()


@tool
def get_hcp_history(hcp_name: str):
    """
    Retrieve all interactions for an HCP.
    """
    db = SessionLocal()
    try:
        print("========== get_hcp_history called ==========")
        print("Looking up:", hcp_name)

        interactions = (
            db.query(HCPInteraction)
            .filter(HCPInteraction.hcp_name == hcp_name)
            .order_by(HCPInteraction.id.desc())
            .all()
        )

        print(f"Found {len(interactions)} interaction(s)")

        if not interactions:
            return json.dumps({"hcp_name": hcp_name, "interactions": []})

        results = []
        for i in interactions:
            results.append({
                "id": i.id,
                "interaction_type": i.interaction_type,
                "date": str(i.date),
                "time": str(i.time),
                "attendees": i.attendees,
                "topics_discussed": i.topics_discussed,
                "materials_shared": i.materials_shared,
                "samples_distributed": i.samples_distributed,
                "sentiment": i.sentiment,
                "outcomes": i.outcomes,
                "follow_up_actions": i.follow_up_actions,
            })

        return json.dumps({"hcp_name": hcp_name, "interactions": results})
    finally:
        db.close()


@tool
def summarize_interaction(hcp_name: str):
    """
    Summarize interactions for an HCP.
    """
    db = SessionLocal()
    try:
        print("========== summarize_interaction called ==========")
        print("Looking up:", hcp_name)

        interactions = (
            db.query(HCPInteraction)
            .filter(HCPInteraction.hcp_name == hcp_name)
            .order_by(HCPInteraction.id.desc())
            .all()
        )

        print(f"Found {len(interactions)} interaction(s)")

        if not interactions:
            return json.dumps({"hcp_name": hcp_name, "summary": ""})

        notes = "\n".join(i.topics_discussed or "" for i in interactions)

        print("Summary:", notes)

        return json.dumps({"hcp_name": hcp_name, "summary": notes})
    finally:
        db.close()


@tool
def suggest_follow_up(hcp_name: str):
    """
    Suggest follow-up based on previous interactions.
    """
    db = SessionLocal()
    try:
        print("========== suggest_follow_up called ==========")
        print("Looking up:", hcp_name)

        interaction = (
            db.query(HCPInteraction)
            .filter(HCPInteraction.hcp_name == hcp_name)
            .order_by(HCPInteraction.id.desc())
            .first()
        )

        if not interaction:
            print("No previous interaction found")
            return json.dumps({"hcp_name": hcp_name, "follow_up_suggestion": ""})

        print("Previous outcome:", interaction.outcomes)

        return json.dumps({
            "hcp_name": hcp_name,
            "follow_up_suggestion": interaction.outcomes or "",
        })
    finally:
        db.close()