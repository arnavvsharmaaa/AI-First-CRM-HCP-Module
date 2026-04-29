# 🧠 AI-First CRM — HCP Module

> A real-time, AI-powered **Log Interaction** screen for pharmaceutical field representatives.
> Describe a doctor visit in plain English — the AI parses it and populates your CRM form automatically.

---

## 📸 Screenshot

![AI-First CRM — Log Interaction Screen](./docs/screenshot.png)

---

## ✨ Features

- **Natural language → structured form** — type a free-form description, get a fully filled form
- **Real-time updates via WebSocket** — no page reload, no polling
- **Field highlight animation** — every AI-updated field briefly flashes blue so you know what changed
- **Clickable follow-up suggestion chips** — one click copies an AI suggestion into the Follow-up Actions field
- **Sentiment selector** — Positive / Neutral / Negative automatically detected by the AI
- **Interaction Type dropdown** — Meeting, Call, Email, Conference set by the AI
- **Thinking indicator** — animated dots + spinner while the agent processes
- **Error handling** — failed API calls show an inline error message; WebSocket drops show a "Reconnecting…" banner
- **Auto-reconnect WebSocket** — transparent recovery after network blips

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite |
| State management | Redux Toolkit |
| Real-time comms | WebSocket (native browser API) |
| Backend | Python FastAPI |
| AI Agent | LangGraph |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Database | PostgreSQL + SQLAlchemy (async) |
| Font | Google Fonts — Inter |
| Styling | Plain CSS with CSS custom properties (no Tailwind) |

---

## 📁 Project Structure

```
hcp-crm/
├── frontend/
│   ├── index.html
│   └── src/
│       ├── components/
│       │   ├── LogInteractionScreen.jsx   ← split-screen layout
│       │   ├── InteractionForm.jsx        ← LEFT panel (read-only form)
│       │   ├── InteractionForm.css
│       │   ├── AIAssistant.jsx            ← RIGHT panel (chat)
│       │   └── AIAssistant.css
│       ├── store/
│       │   ├── index.js                   ← Redux store
│       │   ├── interactionSlice.js        ← form field state
│       │   └── chatSlice.js               ← chat + thinking state
│       └── services/
│           └── websocket.js               ← WS connection + message dispatch
└── backend/
    ├── main.py                            ← FastAPI app entry point
    ├── .env                               ← secrets (not committed)
    ├── routers/
    │   └── interaction.py                 ← /api/chat + /ws/{session_id}
    ├── agent/
    │   ├── graph.py                       ← LangGraph agent definition
    │   ├── state.py                       ← AgentState TypedDict
    │   └── tools/
    │       ├── log_interaction.py
    │       ├── edit_interaction.py
    │       ├── suggest_followups.py
    │       ├── search_hcp.py
    │       └── get_interaction.py
    ├── models/
    │   ├── database.py                    ← async SQLAlchemy engine
    │   ├── interaction.py                 ← Interaction ORM model
    │   └── hcp.py                         ← HCP ORM model
    └── websocket_manager.py               ← session → WebSocket registry
```

---

## ⚙️ Setup Instructions

### Prerequisites

| Tool | Version |
|------|---------|
| Node.js | ≥ 20.19 or ≥ 22.12 (v24+ recommended) |
| Python | ≥ 3.11 |
| PostgreSQL | ≥ 14 |
> ⚠️ Vite 8 requires Node.js v20.19+, v22.12+, or v24+. Earlier versions will fail to start the dev server.

---

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ai-first-crm.git
cd ai-first-crm
```

---

### 2. Backend setup

```bash
cd hcp-crm/backend
```

**Create a virtual environment and install dependencies:**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

**Create the `.env` file:**

```bash
# hcp-crm/backend/.env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/hcp_crm
GROQ_API_KEY=gsk_your_groq_api_key_here
```

> Get a free Groq API key at [https://console.groq.com](https://console.groq.com)

**Create the PostgreSQL database:**

```sql
CREATE DATABASE hcp_crm;
```

**Run database migrations (SQLAlchemy creates tables on startup automatically):**

The tables are created via `Base.metadata.create_all()` in `main.py` on first run.

---

### 3. Frontend setup

```bash
cd hcp-crm/frontend
npm install
```

---

## 🚀 Running the App

Open **two terminal windows**.

### Terminal 1 — Backend

```bash
cd hcp-crm/backend
# Activate venv if not already active
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

uvicorn main:app --reload --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process …
```

### Terminal 2 — Frontend

```bash
cd hcp-crm/frontend
npm run dev
```

You should see:

```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🧠 LangGraph Tools

The AI agent uses a **LangGraph ReAct loop** to decide which tool to call based on the user's message. All tools return a `form_update` payload that the backend broadcasts via WebSocket.

### Tool 1 — `log_interaction`

**Purpose:** Parses a natural language description of a new HCP interaction, extracts all structured fields, saves a new record to PostgreSQL, and returns the complete form payload.

**Extracted fields:** `hcpName`, `interactionType`, `date`, `time`, `attendees`, `topicsDiscussed`, `materialsShared`, `samplesDistributed`, `sentiment`, `outcomes`, `followUpActions`

**Example trigger:**
```
Met Dr. Patel today, discussed MediCure pricing objections, neutral sentiment
```

---

### Tool 2 — `edit_interaction`

**Purpose:** Updates one or more specific fields of the most recently logged interaction. Does NOT create a new record — patches the existing one.

**Example trigger:**
```
Change the sentiment to positive and update outcomes: HCP agreed to a trial
```

---

### Tool 3 — `suggest_followups`

**Purpose:** Generates 3–5 concrete, actionable follow-up suggestions based on the current interaction context (HCP name, topics discussed, sentiment). Suggestions appear as clickable chips in the form.

**Example trigger:**
```
Suggest follow-up actions for the Dr. Patel meeting
```
*(also triggered automatically after `log_interaction`)*

---

### Tool 4 — `search_hcp`

**Purpose:** Searches the HCP database by name and returns matching HCP details (name, specialty, affiliation). Useful for looking up a doctor before logging an interaction.

**Example trigger:**
```
Search for Dr. Mehta in the database
```

---

### Tool 5 — `get_interaction`

**Purpose:** Retrieves a previously logged interaction by HCP name or interaction ID and repopulates the form with the historical data.

**Example trigger:**
```
Show me the last interaction with Dr. Patel
```

---

## 💬 Example Chat Prompts

Test each tool end-to-end with these prompts in the chat panel:

```
# Test Tool 1 — log_interaction
Met Dr. Sarah Johnson today at City Hospital. We discussed OncoBoost Phase III trial data 
and pricing for Q3. She seemed positive. Shared the OncoBoost brochure PDF. Distributed 
2 sample packs of MediCure 10mg.

# Test Tool 2 — edit_interaction  
Actually, change the sentiment to neutral. Also update the outcomes: she wants to review 
the data with her team before committing.

# Test Tool 3 — suggest_followups
Suggest some follow-up actions for the Dr. Johnson meeting about OncoBoost.

# Test Tool 4 — search_hcp
Search for Dr. Patel in the database.

# Test Tool 5 — get_interaction
Show me the last interaction I logged with Dr. Johnson.
```

---

## 🔌 WebSocket Message Format

### Server → Client: Form Update
```json
{
  "type": "form_update",
  "fields": {
    "hcpName": "Dr. Sarah Johnson",
    "sentiment": "positive",
    "topicsDiscussed": "OncoBoost Phase III trial data and Q3 pricing",
    "date": "2026-04-29",
    "time": "10:30",
    "interactionType": "Meeting"
  },
  "ai_message": "Got it! I've logged your interaction with Dr. Sarah Johnson.",
  "interaction_id": "904a927b-f3ec-4cbd-b891-36b70dfdc5b2"
}
```

### Server → Client: Thinking Indicator
```json
{ "type": "thinking", "value": true }
```

### Client → Server: Chat Message (HTTP POST /api/chat)
```json
{
  "message": "Met Dr. Patel today, discussed MediCure pricing, neutral sentiment",
  "session_id": "session_1777460313039"
}
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL async connection string |
| `GROQ_API_KEY` | ✅ | Groq API key for LLM inference |

---

## 📝 License

MIT — feel free to use, modify, and distribute.
