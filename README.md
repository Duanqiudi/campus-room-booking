# Unified Campus Booking Agent

Recovered and reconstructed source code for the final-year project. The application provides one interface for library rooms and sports facilities, with a confirmation-first booking agent and a shared validation backend.

## Structure

- `backend/`: FastAPI, SQLite, booking policy validation, LangGraph adapter, and MCP tools.
- `web/`: Next.js user interface with assistant, resource schedule, and booking history.

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

API documentation is available at `http://127.0.0.1:8000/docs`.

### Frontend

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Agent examples

- `Book D-1012G tomorrow 14:00-15:00 for 2 people`
- `Book badminton tomorrow 18:00-19:00 for 2 people`
- `Show my bookings`
- `Cancel booking bkg_xxxxxxxxxxxx`

The deterministic parser keeps the demonstration usable without an external API key. When `langgraph` is installed, requests are executed through the compiled graph. MCP tools can be started with `python -m app.mcp_server`.
