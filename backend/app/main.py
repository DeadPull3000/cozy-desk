from fastapi import FastAPI

app = FastAPI(title="Study Desk Agent API", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "academic-agent-backend"}
