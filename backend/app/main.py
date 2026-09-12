from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db
from .routers import candidates

app = FastAPI(title="Study Desk Agent API", version="0.1.0")

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidates.router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
        
    return {"status": "healthy", "service": "academic-agent-backend", "database": db_status}
