import json
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from backend.ollama_client import OllamaClient
from backend.symptom_analyzer import SymptomAnalyzer, EMERGENCY_CONTACTS
from backend.emotion_detector import EmotionDetector

app = FastAPI(
    title="BAYMAX Health Companion API",
    description="Backend API for the Big Hero 6 inspired healthcare assistant",
    version="1.0.0"
)

# Enable CORS for browser execution
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
ollama_client = OllamaClient()
analyzer = SymptomAnalyzer()
emotion_detector = EmotionDetector()

# Preload Ollama model asynchronously
ollama_client.preload_model()

# Schemas
class ChatRequest(BaseModel):
    prompt: str

class EmotionRequest(BaseModel):
    image: str  # Base64 data URI

class AnalyzeRequest(BaseModel):
    text: str

# Endpoints
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Streams the assistant response from Ollama as Server-Sent Events (SSE).
    """
    async def sse_generator():
        # Using a standard generator inside async helper for SSE formatting
        for chunk in ollama_client.stream_response(request.prompt):
            data = json.dumps({"text": chunk})
            yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@app.post("/api/analyze-symptoms")
async def analyze_symptoms_endpoint(request: AnalyzeRequest):
    """
    Analyzes symptoms, checks for emergency warning signs, and retrieves
    contextual clinical trials (ClinicalTrials.gov) and drug warnings (OpenFDA).
    """
    try:
        results = analyzer.analyze_query(request.text)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/detect-emotion")
async def detect_emotion_endpoint(request: EmotionRequest):
    """
    Takes webcam frame snapshot (base64) and performs emotion detection.
    """
    try:
        result = emotion_detector.detect_emotion(request.image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wearable")
async def wearable_endpoint():
    """
    Mock endpoint generating dynamic, highly realistic wearable biosignals.
    """
    import random
    from datetime import datetime
    
    # Simulate realistic fluctuations around standard biosigns
    hr = random.randint(68, 76)
    spo2 = random.randint(97, 99)
    steps = random.randint(3500, 8500)
    sleep = round(random.uniform(6.0, 7.8), 1)
    
    return {
        "heart_rate": hr,
        "spo2": spo2,
        "steps_today": steps,
        "sleep_hours": sleep,
        "activity_level": "Moderate" if steps > 5000 else "Sedentary",
        "last_sync": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/api/emergency")
async def emergency_endpoint(region: str = "india"):
    """
    Retrieves region-specific emergency numbers.
    """
    region_lower = region.lower()
    contacts = EMERGENCY_CONTACTS.get(region_lower, EMERGENCY_CONTACTS["global"])
    return {
        "region": region_lower,
        "police": contacts.get("police", "112"),
        "ambulance": contacts.get("ambulance", "112"),
        "note": contacts.get("note", "")
    }

# Serving the static frontend directory.
# API routes must be registered before mounting the catch-all StaticFiles directory.
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
else:
    @app.get("/")
    async def index_fallback():
        return {"message": "FastAPI is running, but frontend/ directory was not found. Place your web assets in frontend/."}
