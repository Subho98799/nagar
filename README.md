#RACHI HACKS 2026 , GDG RANCHI


# Nagar Alert Hub - Backend

A WhatsApp-first civic alert system for Tier-2 and Tier-3 cities in India.

## Design Principles

- ✅ AI **assists** interpretation, does NOT verify truth
- ✅ Human-in-the-loop exists only for high-impact alerts
- ✅ No automated authority escalation
- ✅ No prediction or forecasting
- ✅ Simple, readable, and demo-safe

## Tech Stack

- **Backend**: Python FastAPI
- **Database**: Firebase Firestore
- **AI**: Gemini API (to be added)
- **Deployment**: Render / Railway

## Project Structure

```
/app
  ├── main.py                # FastAPI app entry point
  ├── config/
  │     └── firebase.py      # Firestore initialization
  ├── routes/
  │     └── health.py        # Health check endpoints
  ├── models/
  │     └── base.py          # Pydantic base models (placeholders)
  ├── services/
  │     └── __init__.py      # Business logic layer (empty for now)
  └── core/
        └── settings.py      # Environment variables & config
```

## Setup Instructions

### 1. Prerequisites

- Python 3.10+
- Firebase project with Firestore enabled
- Service account JSON key from Firebase

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example env file (Unix / macOS)
cp .env.example .env

# Copy the example env file (Windows PowerShell)
Copy-Item .env.example .env
```

Edit the created `.env` and add your Firebase credentials. See `.env.example` in the repository for all available keys and recommended defaults. On Windows, set `FIREBASE_CREDENTIALS_PATH` to the full path of your service account JSON (for example: `C:\\full\\path\\to\\serviceAccountKey.json`).

Example minimal `.env` entries:

```ini
# FIREBASE_PROJECT_ID=your-project-id
# FIREBASE_CREDENTIALS_PATH=C:\\full\\path\\to\\serviceAccountKey.json
# DEBUG=True
```

### 4. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project (or use existing)
3. Enable Firestore Database
4. Go to Project Settings → Service Accounts
5. Generate new private key (downloads JSON file)
6. Save the JSON file as `serviceAccountKey.json` in project root
7. Update `FIREBASE_PROJECT_ID` and `FIREBASE_CREDENTIALS_PATH` in `.env`

### 5. Run the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8000
```

The server will start at: `http://localhost:8000`

### 6. Test Endpoints

- **API Docs**: http://localhost:8000/docs
- **Root**: http://localhost:8000/
- **Health Check**: http://localhost:8000/health
- **Database Health**: http://localhost:8000/health/db

## What's Working Now (Step 1)

✅ FastAPI server running  
✅ CORS enabled for frontend  
✅ Firestore connection initialized  
✅ Health check endpoints  
✅ Environment variable configuration  
✅ Clean project structure  

## What's NOT Included Yet

❌ WhatsApp API integration  
❌ Gemini AI logic  
❌ Alert processing  
❌ Authentication  
❌ Admin dashboard logic  
❌ Authority escalation  

## Next Steps

- Step 2: Add data models and Firestore CRUD operations
- Step 3: Integrate Gemini API for alert interpretation assistance
- Step 4: Add WhatsApp webhook handlers
- Step 5: Implement human-in-the-loop workflow for high-impact alerts

## Deployment

Ready for deployment to:
- [Render](https://render.com/)
- [Railway](https://railway.app/)

Deployment instructions will be added in later steps.

---

**Note**: This is Step 1 scaffold only. DO NOT jump ahead to implementing business logic.
