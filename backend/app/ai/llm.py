import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Used for structured tasks: intent classification (chat_service.py/agent.py)
# and field extraction (tools.py). Kept at temperature=0 so tool-call JSON
# and extracted fields stay reliable and reproducible. Using the 70b model
# here instead of 8b-instant, since 8b was repeatedly malforming tool-call
# JSON on short/typo-heavy messages.
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0,
    max_tokens=512,
)

# Used only for the conversational agent (graph.py) — the model that
# actually replies in chat, including greetings/small talk. A moderate
# temperature here means "hello" doesn't produce the exact same canned
# sentence every time, without affecting the reliability of tool argument
# formatting done by the `llm` instance above.
conversational_llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0,
    max_tokens=512,
)