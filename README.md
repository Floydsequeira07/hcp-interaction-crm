# HCP Interaction CRM

An AI-assisted CRM for logging and managing Healthcare Professional (HCP) interactions. Field reps can describe a visit, call, meeting, or conference in plain English through a chat assistant, and the app automatically extracts structured data, fills in the interaction form, and saves it to a MySQL database — no manual form-filling required.

## Features

- **Natural language logging** — type something like *"Visited Dr. Sharma today, discussed Product X, positive feedback"* and the AI extracts and saves all relevant fields.
- **Automatic form population** — extracted fields (HCP name, interaction type, date, time, attendees, topics, materials shared, samples distributed, sentiment, outcomes, follow-up actions) populate the on-screen form live.
- **Natural language corrections** — made a mistake? Just say *"Sorry, the doctor's name is Dr. Smith"* or *"the sentiment is neutral"* and the AI updates only that field on the most recently logged interaction, leaving everything else untouched.
- **Smart date/time resolution** — understands relative terms like "today", "yesterday", and "tomorrow" and resolves them to the correct real calendar date, or uses an explicit date/time if you provide one.
- **Tool-based AI agent** — built on LangGraph's ReAct agent pattern, routing each message to the correct action: logging, editing, viewing history, summarizing, or suggesting follow-ups.
- **MySQL persistence** — every interaction is validated with Pydantic and stored in a MySQL database via SQLAlchemy.

## Tech Stack

**Backend**
- FastAPI (Python)
- LangChain + LangGraph (agent orchestration)
- Groq API (`llama-3.1-8b-instant`) for LLM extraction and conversation
- SQLAlchemy + MySQL for persistence
- Pydantic for data validation

**Frontend**
- React (Vite)
- Redux Toolkit for state management
- Tailwind-style component CSS
- Lucide React icons

## Project Structure

```
hcp-interaction-crm/
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── agent.py          # Orchestrates the chat request/response cycle
│   │   │   ├── graph.py          # LangGraph agent definition + system prompt
│   │   │   ├── llm.py            # Groq LLM client configuration
│   │   │   └── tools.py          # log_interaction, edit_interaction, and other agent tools
│   │   ├── routers/
│   │   │   ├── ai.py             # /ai/chat endpoint
│   │   │   └── interaction.py    # CRUD endpoints for interactions
│   │   ├── crud.py               # Database operations
│   │   ├── database.py           # SQLAlchemy engine/session setup
│   │   ├── models.py             # HCPInteraction ORM model
│   │   ├── schemas.py            # Pydantic schemas (InteractionCreate, etc.)
│   │   └── main.py               # FastAPI app entrypoint
│   ├── venv/                     # Python virtual environment (not tracked in git)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AIChat.jsx        # Chat assistant UI
│   │   │   └── HCPForm.jsx       # Interaction form UI
│   │   ├── features/interaction/
│   │   │   └── interactionSlice.js  # Redux slice for form state
│   │   ├── pages/
│   │   │   └── Dashboard.jsx
│   │   ├── services/
│   │   │   ├── aiService.js
│   │   │   └── interactionApi.js
│   │   ├── app/store.js          # Redux store configuration
│   │   └── main.jsx
│   └── package.json
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js and npm
- MySQL server running locally
- A Groq API key ([console.groq.com](https://console.groq.com))

### Backend Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1      # Windows PowerShell
# source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file in `backend/` with:
```
GROQ_API_KEY=your_groq_api_key_here
```

Configure your MySQL connection in `app/database.py`, then start the server:
```bash
uvicorn app.main:app --reload
```
Backend runs at `http://127.0.0.1:8000`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`.

## How It Works

1. The user types a message in the **AI Assistant** chat panel (e.g. *"Called Dr. Iyer yesterday about Product Y dosing, gave 10 samples, sentiment neutral"*).
2. The message is sent to the backend's `/ai/chat` endpoint.
3. A LangGraph agent decides which tool to call:
   - **`log_interaction`** — for a brand-new interaction with an HCP name and description
   - **`edit_interaction`** — for a correction to the most recently logged interaction
   - **`get_hcp_history`**, **`summarize_interaction`**, **`suggest_follow_up`** — for other CRM queries
4. The relevant tool calls Groq's LLM to extract structured fields, resolves any relative dates/times, validates the data with Pydantic, and saves it to MySQL.
5. The extracted/updated data is returned to the frontend, which updates the Redux store and automatically fills in the **HCP Interaction Form** on the left side of the screen.
6. A natural-language confirmation message appears in the chat, summarizing which fields were filled in or changed.

## Notes on Rate Limits

This project uses Groq's free tier, which enforces both daily and per-minute token limits. If you see `rate_limit_exceeded` errors in the backend terminal, wait for the cooldown period indicated in the error message, or consider upgrading to a paid Groq tier for heavier usage.

## Author
Floyd Jostin Sequeira
