# Baymax Healthcare Assistant 🏥🤖

An interview-grade, high-fidelity medical companion application inspired by Baymax from *Big Hero 6*. This project features a modern **FastAPI** backend integrated with local **Ollama** LLMs, dynamic emotion analysis via facial recognition, biosignal syncing, and automated evidence lookups connecting directly to public healthcare registries (ClinicalTrials.gov & OpenFDA).

---

## 📌 Features

### 🖥️ High-Tech HUD Web Interface
- **Pulsing Baymax Link**: SVG visualization of Baymax's eyes that blinks and animates in sync with speech output.
- **Biometric Heartwave**: A live, scrolling canvas-based ECG grid and heartbeat monitor.
- **Body Scanner Map**: Interactive humanoid wireframe SVG allowing patients to tap/click specific regions (e.g. Head, Chest) to automatically select target symptom inputs.
- **Ambient Scanlines & Transitions**: Glassmorphism dashboard styled with modern typography, dark glowing neon aesthetics, CSS variables, and fluid transitions.

### ⚙️ Robust FastAPI Backend Services
- **Ollama Integration**: Automated connection check and background service launcher (`ollama serve`) with Server-Sent Events (SSE) chat streaming.
- **Patient Emotion Tracking**: Real-time evaluation of webcam snapshots (base64) using facial expression recognition libraries (`FER` or Haar Cascade fallback), plotting bounding boxes on the overlay.
- **Medical Registry Integrations**:
  - **ClinicalTrials.gov API**: Searches active recruiting studies in real-time matching evaluated symptoms.
  - **OpenFDA API**: Looks up chemical/drug warnings, brand generic facts, and indications if medications (e.g. Metformin, Aspirin) are typed.
- **Wearable Biosignals**: Simulated health band sync returning heart rate (SpO2), daily steps, sleep quality, and active level data.
- **Emergency Action Centre**: Quick dispatch region selectors (India, US/UK, Global) and panic overlay flash systems with voice warning protocols.

### 🎙️ Web-Native Speech Controls
- **Speech Synthesis (TTS)**: Custom voice output using browser-native SpeechSynthesis. Speaks responses with a soft, robotic, deliberate tempo matching Baymax's cinematic voice.
- **Speech Recognition (STT)**: Fully native hands-free voice transcription directly inputting queries.

---

## 📂 Project Structure
```
Baymax/
├── backend/
│   ├── __init__.py
│   ├── main.py              # Central FastAPI application & endpoint routing
│   ├── ollama_client.py     # Ollama connection manager & completion streams
│   ├── symptom_analyzer.py  # Symptom triage, OpenFDA & ClinicalTrials lookups
│   └── emotion_detector.py  # Webcam frames base64 image decoding & FER/Haar analysis
├── frontend/
│   ├── index.html           # Dashboard layout structures & SVG charts
│   ├── style.css            # Custom CSS styles, variables, grid system & animations
│   └── app.js               # Canvas drawers, webcam polling, speech loops & SSE
├── requirements.txt         # Project package requirements
├── main.py                  # Entry runner (starts FastAPI and launches default browser)
├── LICENSE                  # Apache 2.0 License
└── README.md                # Documentation
```

---

## 🚀 Getting Started

### Prerequisites
1. **Python 3.9+** installed.
2. **Ollama** installed on your system.
   - [Download Ollama here](https://ollama.com/)
   - Pre-pull the default model:
     ```bash
     ollama pull mistral
     ```

### 1. Install Dependencies
Run the package installer inside your terminal virtual environment:
```bash
pip install -r requirements.txt
```

### 2. Run the Application
Start the application using the entry-point script:
```bash
python main.py
```
This script will:
1. Boot the FastAPI web server on `http://127.0.0.1:8000`.
2. Connect to local Ollama and auto-launch `ollama serve` if down.
3. Automatically launch your default web browser directly to the dashboard interface.

---

## 👨‍💻 License & Attributions
This project is licensed under the **Apache License 2.0** – see the [LICENSE](LICENSE) file for details.

### Attribution
If you distribute or use this project, **you must credit the original author by linking to this repository** and **include the LICENSE file**.

---

## ⚠️ Disclaimer
This project is for **educational and portfolio purposes only**. It should **never replace professional medical advice, diagnosis, or treatment**. Always consult a licensed healthcare professional for any health-related concerns.
