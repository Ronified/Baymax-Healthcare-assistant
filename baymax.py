"""
Baymax AI — JARVIS-style medical assistant (streaming + cancel + preload)

Changes vs your version:
  - Streams responses from Ollama so the UI never feels frozen
  - Separate connect/read timeouts to prevent indefinite hangs
  - "Cancel" button to stop a running generation safely
  - Preloads the model at startup to avoid first-response lag
  - Thread-safe UI updates via Tkinter's `after()`

Requirements:
    - Python 3.8+
    - ollama installed & in PATH  → https://ollama.com
    - pip install -r requirements.txt

requirements.txt (example):
    requests>=2.31.0
    SpeechRecognition>=3.10.0   # optional, for mic input
    PyAudio                      # optional; on Windows use: pipwin install pyaudio
    pyttsx3>=2.90               # optional, for TTS

Notes:
    - On Windows, if PyAudio fails: `pip install pipwin && pipwin install pyaudio`.
    - Ollama default port is 11434.
    - This script will try to auto-start Ollama via `ollama serve` and then poll until ready.
"""

import os
import sys
import time
import json
import threading
import subprocess
from datetime import datetime

import requests
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox

# optional: speech and tts (script still runs without them)
try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

# -----------------------------
# Config
# -----------------------------
OLLAMA_URL = "http://localhost:11434"
API_GENERATE = OLLAMA_URL + "/api/generate"
MODEL_NAME = "mistral"            # user-requested model
OLLAMA_START_CMD = ["ollama", "serve"]
OLLAMA_START_WAIT = 40             # seconds to wait for Ollama to become available
# Use tuple timeout: (connect_timeout, read_timeout-per-chunk)
REQUEST_CONNECT_TIMEOUT = 10
REQUEST_READ_TIMEOUT = 120
VOICE_RATE = 170
SPEAK_RESPONSES_DEFAULT = True

EMERGENCY_KEYWORDS = [
    "chest pain", "severe chest pain", "shortness of breath", "difficulty breathing",
    "unconscious", "fainting", "severe bleeding", "heavy bleeding",
    "stroke", "slurred speech", "sudden weakness", "sudden numbness",
    "severe allergic reaction", "anaphylaxis", "not breathing", "broken bone", "fracture"
]

conversation_history = []
history_lock = threading.Lock()

# -----------------------------
# Utility: Ollama server management
# -----------------------------

def is_ollama_running():
    try:
        resp = requests.get(OLLAMA_URL, timeout=2)
        return resp.status_code in (200, 404)  # 404 at root is fine; server is up
    except requests.RequestException:
        return False


def start_ollama_in_background():
    """Attempt to start Ollama. Return Popen if started, else None."""
    try:
        p = subprocess.Popen(
            OLLAMA_START_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )
        return p
    except FileNotFoundError:
        return None
    except Exception as e:
        print("Error starting Ollama:", e)
        return None


def ensure_ollama_running(timeout=OLLAMA_START_WAIT):
    if is_ollama_running():
        print("✅ Ollama already running.")
        return True

    print("🔄 Ollama not running. Attempting to start Ollama in background...")
    proc = start_ollama_in_background()
    if proc is None:
        print("❌ Could not start Ollama: 'ollama' not found in PATH.")
        print("Install Ollama (https://ollama.com) and ensure `ollama` works in your terminal.")
        return False

    start_t = time.time()
    while time.time() - start_t < timeout:
        if is_ollama_running():
            print("✅ Ollama is now running.")
            return True
        time.sleep(1)
    print("❌ Timeout waiting for Ollama to start.")
    return False


# -----------------------------
# Model interaction (Streaming)
# -----------------------------

def build_system_prompt():
    return (
        "You are JARVIS AI, a helpful and safety-aware medical assistant. "
        "Provide clear evidence-based general medical information, suggest when to see a licensed professional, "
        "and advise immediate emergency action (call emergency services) when appropriate."
    )


def generate_stream(prompt_text):
    """
    Generator that yields response chunks from Ollama as they arrive.
    Raises requests.RequestException on network/HTTP errors.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": f"{build_system_prompt()}\nUser: {prompt_text}\nAssistant:",
        "stream": True,
    }

    with requests.post(
        API_GENERATE,
        json=payload,
        timeout=(REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT),
        stream=True,
    ) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines():
            if not raw:
                continue
            try:
                chunk = json.loads(raw.decode("utf-8"))
            except Exception:
                # Best-effort fallback if line is not JSON
                yield raw.decode("utf-8")
                continue

            # Ollama streaming returns objects with a `response` field and a final {"done": true}
            if isinstance(chunk, dict):
                if chunk.get("response"):
                    yield chunk["response"]
                if chunk.get("done"):
                    break


def preload_model():
    """Touch the model once so the first real call is snappy. Ignore failures."""
    try:
        payload = {"model": MODEL_NAME, "prompt": " ", "stream": False}
        requests.post(API_GENERATE, json=payload, timeout=(5, 15))
    except Exception:
        pass


# -----------------------------
# TTS (pyttsx3) wrapper
# -----------------------------

tts_engine = None


def init_tts():
    global tts_engine
    if pyttsx3 is None:
        print("⚠️ pyttsx3 not installed. TTS disabled.")
        return
    try:
        tts_engine = pyttsx3.init()
        tts_engine.setProperty("rate", VOICE_RATE)
    except Exception as e:
        print("⚠️ TTS init failed:", e)
        tts_engine = None


def speak_text(text):
    if tts_engine is None:
        return
    try:
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception as e:
        print("⚠️ TTS error:", e)


# -----------------------------
# Emergency detection
# -----------------------------

def detect_emergency(text):
    lower = text.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw in lower:
            return True, kw
    return False, None


# -----------------------------
# GUI helpers and app logic
# -----------------------------

class BaymaxApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS AI Medical Chatbot — Baymax")
        self.root.geometry("920x660")
        self.speak_responses = SPEAK_RESPONSES_DEFAULT

        # runtime state
        self.current_thread = None
        self.cancel_event = threading.Event()
        self.streaming_locked = threading.Lock()  # to avoid overlapping writes

        # menu
        men = tk.Menu(root)
        root.config(menu=men)
        file_menu = tk.Menu(men, tearoff=0)
        men.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save conversation (JSON)", command=self.save_chat)
        file_menu.add_command(label="Export as text", command=self.export_plain_text)
        file_menu.add_separator()
        file_menu.add_command(label="Clear chat", command=self.clear_chat)
        file_menu.add_command(label="Exit", command=root.quit)
        men.add_command(label="Settings", command=self.open_settings)

        header = tk.Frame(root, bg="#0f1720")
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="JARVIS AI — Medical Assistant (Baymax)",
            font=("Consolas", 16, "bold"),
            fg="#00FFAB",
            bg="#0f1720",
        ).pack(side=tk.LEFT, padx=10, pady=8)

        wear_btn = tk.Button(header, text="Fetch Wearable Data", command=self.fetch_wearable)
        wear_btn.pack(side=tk.RIGHT, padx=10)

        # chat window
        self.chat_window = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#07080a",
            fg="#00FFAB",
            font=("Consolas", 12),
        )
        self.chat_window.pack(padx=12, pady=(6, 8), fill=tk.BOTH, expand=True)

        # entry frame
        entry_frame = tk.Frame(root, bg="#0f1720")
        entry_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        self.user_entry = tk.Entry(
            entry_frame,
            font=("Consolas", 12),
            bg="#222222",
            fg="#ffffff",
            insertbackground="white",
        )
        self.user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.user_entry.bind("<Return>", self.on_send)

        send_btn = tk.Button(entry_frame, text="Send", command=self.on_send, bg="#00FFAB", fg="#081010")
        send_btn.pack(side=tk.LEFT)

        mic_btn = tk.Button(entry_frame, text="🎙️ Speak", command=self.on_speak, bg="#00FFAB", fg="#081010")
        mic_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.cancel_btn = tk.Button(entry_frame, text="Cancel", command=self.on_cancel, bg="#ef4444", fg="#ffffff")
        self.cancel_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.cancel_btn.config(state=tk.DISABLED)

        # welcome
        self.safe_insert("👋 Hi! I'm BAYMAX (JARVIS AI upgraded). Ask me anything health-related. Type or use the mic.\n\n")

    # ----- Thread-safe UI helpers -----
    def _append_text(self, text: str):
        self.chat_window.config(state=tk.NORMAL)
        self.chat_window.insert(tk.END, text)
        self.chat_window.config(state=tk.DISABLED)
        self.chat_window.yview(tk.END)

    def safe_insert(self, text: str):
        self.root.after(0, self._append_text, text)

    # ----- Event handlers -----
    def on_send(self, event=None):
        txt = self.user_entry.get().strip()
        if not txt:
            return
        self.user_entry.delete(0, tk.END)
        self.submit_user_message(txt, source="text")

    def on_speak(self):
        if sr is None:
            self.safe_insert("❌ SpeechRecognition not installed or unavailable. Install it to use voice.\n\n")
            return
        threading.Thread(target=self.listen_and_submit, daemon=True).start()

    def on_cancel(self):
        # Signal cancellation and let the worker exit gracefully
        self.cancel_event.set()
        self.safe_insert("⏹️ Cancel requested. Stopping current response...\n\n")

    # ----- Chat flow -----
    def set_busy(self, busy: bool):
        if busy:
            self.cancel_btn.config(state=tk.NORMAL)
        else:
            self.cancel_btn.config(state=tk.DISABLED)

    def submit_user_message(self, text, source="text"):
        if self.current_thread and self.current_thread.is_alive():
            self.safe_insert("⚠️ A response is already in progress. Click 'Cancel' to stop it.\n\n")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with history_lock:
            conversation_history.append({"role": "user", "text": text, "time": timestamp})
        self.safe_insert(f"🧑 You ({source}): {text}\n")

        # emergency check
        is_em, kw = detect_emergency(text)
        if is_em:
            emergency_msg = (
                "⚠️ I detected possible emergency symptoms (keyword: '{}'). If this is life-threatening, "
                "please call your local emergency services immediately (e.g., 112/911). I can provide basic first-aid info while help is on the way."
            ).format(kw)
            with history_lock:
                conversation_history.append({
                    "role": "assistant",
                    "text": emergency_msg,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
            self.safe_insert(f"🤖 JARVIS AI: {emergency_msg}\n\n")
            if self.speak_responses:
                threading.Thread(target=speak_text, args=(emergency_msg,), daemon=True).start()
            return

        self.cancel_event.clear()
        self.set_busy(True)
        self.safe_insert("🤖 JARVIS AI: ")  # prefix line; stream will append

        def worker(user_text: str):
            resp_accum = []
            error_text = None
            try:
                for chunk in generate_stream(user_text):
                    if self.cancel_event.is_set():
                        break
                    if chunk:
                        resp_accum.append(chunk)
                        # append chunk to UI
                        self.safe_insert(chunk)
                # newline finish
                self.safe_insert("\n\n")
            except requests.RequestException as e:
                error_text = f"Error contacting model: {e}"
            except Exception as e:
                error_text = f"Unexpected error: {e}"
            finally:
                final_text = "".join(resp_accum)
                if self.cancel_event.is_set():
                    final_text = final_text + "\n(Generation canceled by user.)"
                if error_text:
                    self.safe_insert(error_text + "\n\n")
                    final_text = error_text
                # record to history
                with history_lock:
                    conversation_history.append({
                        "role": "assistant",
                        "text": final_text,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                # optional TTS
                if self.speak_responses and final_text and not self.cancel_event.is_set():
                    threading.Thread(target=speak_text, args=(final_text,), daemon=True).start()
                # reset busy
                self.set_busy(False)

            
        self.current_thread = threading.Thread(target=worker, args=(text,), daemon=True)
        self.current_thread.start()

    def listen_and_submit(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                self.safe_insert("🎤 Listening (speak now)...\n")
                audio = recognizer.listen(source, phrase_time_limit=8)
            try:
                transcript = recognizer.recognize_google(audio)
                self.safe_insert(f"🧑 You (voice): {transcript}\n")
                self.submit_user_message(transcript, source="voice")
            except sr.UnknownValueError:
                self.safe_insert("❌ Could not understand audio. Try again.\n\n")
            except sr.RequestError as e:
                self.safe_insert(f"❌ Speech recognition service error: {e}\n\n")
        except Exception as e:
            self.safe_insert(f"❌ Microphone error: {e}\n\n")

    def fetch_wearable(self):
        data = {
            "hr": 72,
            "steps_today": 4200,
            "sleep_hours": 6.5,
            "last_sync": datetime.utcnow().isoformat() + "Z",
        }
        self.safe_insert(f"📟 Wearable: {json.dumps(data, indent=0)}\n\n")

    def clear_chat(self):
        if messagebox.askyesno("Clear chat", "Are you sure you want to clear the conversation history?"):
            self.chat_window.config(state=tk.NORMAL)
            self.chat_window.delete("1.0", tk.END)
            self.chat_window.config(state=tk.DISABLED)
            with history_lock:
                conversation_history.clear()

    def save_chat(self):
        with history_lock:
            if not conversation_history:
                messagebox.showinfo("Save chat", "No messages to save.")
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("Text files", "*.txt")],
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                json.dump(conversation_history, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Saved", f"Conversation saved to {path}")

    def export_plain_text(self):
        with history_lock:
            if not conversation_history:
                messagebox.showinfo("Export", "No messages to export.")
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".txt", filetypes=[("Text files", "*.txt")]
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                for msg in conversation_history:
                    f.write(f"[{msg['time']}] {msg['role'].upper()}: {msg['text']}\n")
            messagebox.showinfo("Exported", f"Plain text exported to {path}")

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("480x320")

        tk.Label(win, text="Model Endpoint (URL):").pack(anchor=tk.W, padx=10, pady=(10, 0))
        ep_entry = tk.Entry(win, width=80)
        ep_entry.insert(0, API_GENERATE)
        ep_entry.pack(padx=10)

        tk.Label(win, text="Model name:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        model_entry = tk.Entry(win, width=40)
        model_entry.insert(0, MODEL_NAME)
        model_entry.pack(padx=10)

        tk.Label(win, text="Connect timeout (sec):").pack(anchor=tk.W, padx=10, pady=(10, 0))
        to_conn_entry = tk.Entry(win, width=10)
        to_conn_entry.insert(0, str(REQUEST_CONNECT_TIMEOUT))
        to_conn_entry.pack(padx=10)

        tk.Label(win, text="Read timeout per chunk (sec):").pack(anchor=tk.W, padx=10, pady=(10, 0))
        to_read_entry = tk.Entry(win, width=10)
        to_read_entry.insert(0, str(REQUEST_READ_TIMEOUT))
        to_read_entry.pack(padx=10)

        speak_var = tk.BooleanVar(value=self.speak_responses)
        tk.Checkbutton(win, text="Speak responses (TTS)", variable=speak_var).pack(
            anchor=tk.W, padx=10, pady=(10, 0)
        )

        def save_and_close():
            global API_GENERATE, MODEL_NAME, REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT
            API_GENERATE = ep_entry.get().strip() or API_GENERATE
            MODEL_NAME = model_entry.get().strip() or MODEL_NAME
            try:
                REQUEST_CONNECT_TIMEOUT = int(to_conn_entry.get().strip())
            except Exception:
                pass
            try:
                REQUEST_READ_TIMEOUT = int(to_read_entry.get().strip())
            except Exception:
                pass
            self.speak_responses = bool(speak_var.get())
            win.destroy()
            messagebox.showinfo("Settings", "Saved settings. Changes to endpoint may require restart.")

        tk.Button(win, text="Save", command=save_and_close).pack(pady=12)


# -----------------------------
# Main entry
# -----------------------------

def main():
    # 1) Ensure Ollama server is running (auto-start if needed)
    ok = ensure_ollama_running(timeout=OLLAMA_START_WAIT)
    if not ok:
        print("Please install Ollama (https://ollama.com) and ensure `ollama serve` works from a terminal.")
        try:
            if not messagebox.askyesno(
                "Ollama not running",
                "Ollama server not running and could not be started.\nContinue anyway (you must have a different endpoint configured)?",
            ):
                return
        except Exception:
            # In case Tk is not yet initialized on some platforms
            return

    # 2) Initialize TTS if available
    init_tts()

    # 3) Preload model once so first real call is faster
    preload_model()

    # 4) Start GUI
    root = tk.Tk()
    app = BaymaxApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
