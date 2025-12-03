# Copyright (c) 2025 Mihir Kumar. All Rights Reserved.
# BAYMAX (JARVIS Medical AI) — with camera, India emergency numbers, and emotion polling.

import json
import threading
import subprocess
import time
import platform
from datetime import datetime

import requests
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox

# optional: speech + TTS
try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

# optional: camera + emotion libs
try:
    import cv2
except Exception:
    cv2 = None

try:
    from fer import FER
except Exception:
    FER = None

# -----------------------------
# Config
# -----------------------------
OLLAMA_URL = "http://localhost:11434"
API_GENERATE = OLLAMA_URL + "/api/generate"
MODEL_NAME = "mistral"
OLLAMA_START_CMD = ["ollama", "serve"]
OLLAMA_START_WAIT = 40  # seconds to wait for Ollama to boot

REQUEST_CONNECT_TIMEOUT = 10
REQUEST_READ_TIMEOUT = 120

VOICE_RATE = 170
SPEAK_RESPONSES_DEFAULT = True
ENABLE_CAMERA_DEFAULT = False       # camera off by default; toggle in settings
EMOTION_POLL_INTERVAL = 2.0         # seconds between emotion checks
FRAME_DOWNSCALE = 0.5               # resize factor for faster emotion detection

# Emergency keywords (simple substring check)
EMERGENCY_KEYWORDS = [
    "chest pain", "severe chest pain", "shortness of breath", "difficulty breathing",
    "unconscious", "fainting", "severe bleeding", "heavy bleeding",
    "stroke", "slurred speech", "sudden weakness", "sudden numbness",
    "severe allergic reaction", "anaphylaxis", "not breathing", "broken bone", "fracture"
]

# Emergency contact defaults (can change region in Settings)
EMERGENCY_CONTACTS = {
    "india": {
        "police": "112",
        "ambulance": "108",
        "note": "112 is pan-India emergency. 108 is a common ambulance number in many states."
    },
    "global": {
        "police": "112",
        "ambulance": "112",
        "note": "Use your local emergency number if different."
    },
    "us_uk": {
        "police": "911 / 999",
        "ambulance": "911 / 999",
        "note": "911 (US), 999 or 112 (UK)."
    },
}
DEFAULT_CONTACT_REGION = "india"

conversation_history = []
history_lock = threading.Lock()

# -----------------------------
# Ollama server management
# -----------------------------
def is_ollama_running():
    try:
        resp = requests.get(OLLAMA_URL, timeout=2)
        return resp.status_code in (200, 404)
    except requests.RequestException:
        return False


def start_ollama_in_background():
    """Attempt to start Ollama server."""
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
    """Ensure Ollama is running; try to auto-start if not."""
    if is_ollama_running():
        print("✅ Ollama already running.")
        return True

    print("🔄 Ollama not running. Attempting to start Ollama...")
    proc = start_ollama_in_background()
    if proc is None:
        print("❌ Could not start Ollama: 'ollama' not found.")
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
# LLM interaction
# -----------------------------
def build_system_prompt():
    return (
        "You are JARVIS AI, a helpful and safety-aware medical assistant called BAYMAX. "
        "You provide clear, evidence-based general medical information, NOT diagnosis. "
        "You always remind users to consult a licensed doctor for diagnosis or treatment. "
        "If the user mentions severe or life-threatening symptoms, strongly advise calling "
        "their local emergency number immediately."
    )


def generate_stream(prompt_text: str):
    """
    Stream response chunks from Ollama.
    Yields text pieces.
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
                yield raw.decode("utf-8")
                continue

            if isinstance(chunk, dict):
                if chunk.get("response"):
                    yield chunk["response"]
                if chunk.get("done"):
                    break


def preload_model():
    """One dummy call so first real call is faster."""
    try:
        payload = {"model": MODEL_NAME, "prompt": " ", "stream": False}
        requests.post(API_GENERATE, json=payload, timeout=(5, 15))
    except Exception:
        pass

# -----------------------------
# TTS
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


def speak_text(text: str):
    if not text or tts_engine is None:
        return
    try:
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception as e:
        print("⚠️ TTS error:", e)

# -----------------------------
# Emergency detection
# -----------------------------
def detect_emergency(text: str):
    lower = text.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw in lower:
            return True, kw
    return False, None

# -----------------------------
# Camera + emotion helpers
# -----------------------------
def try_open_camera(max_index=3, extra_backends=True):
    """
    Try to open webcam robustly.
    Returns a cv2.VideoCapture or None.
    """
    if cv2 is None:
        return None

    system = platform.system().lower()
    backends = [None]

    if extra_backends:
        if "windows" in system:
            backends += [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_FFMPEG]
        elif "linux" in system:
            backends += [cv2.CAP_V4L2, cv2.CAP_FFMPEG]
        elif "darwin" in system:
            backends += [cv2.CAP_AVFOUNDATION, cv2.CAP_QT]
        else:
            backends += [cv2.CAP_FFMPEG]

    for idx in range(max_index + 1):
        for backend in backends:
            cap = None
            try:
                if backend is None:
                    cap = cv2.VideoCapture(idx)
                else:
                    cap = cv2.VideoCapture(idx, backend)

                if not cap or not cap.isOpened():
                    if cap:
                        cap.release()
                    continue

                ret, _ = cap.read()
                if ret:
                    return cap
                else:
                    cap.release()
            except Exception:
                try:
                    if cap:
                        cap.release()
                except Exception:
                    pass
    return None


class EmotionDetector:
    """
    Uses FER if available, else simple haar cascade to detect 'neutral' when face present.
    """
    def __init__(self):
        self.detector = None
        self.haar = None

        if FER is not None and cv2 is not None:
            try:
                self.detector = FER(mtcnn=False)
            except Exception:
                self.detector = None

        if cv2 is not None:
            try:
                self.haar = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                )
            except Exception:
                self.haar = None

    def detect(self, frame):
        """
        Return (label, score) or (None, 0.0)
        """
        if frame is None:
            return None, 0.0

        h, w = frame.shape[:2]
        small = cv2.resize(frame, (int(w * FRAME_DOWNSCALE), int(h * FRAME_DOWNSCALE)))

        # Prefer FER if available
        if self.detector is not None:
            try:
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                data = self.detector.detect_emotions(rgb)
                if data:
                    scores = data[0]["emotions"]
                    label = max(scores, key=scores.get)
                    return label, float(scores[label])
            except Exception:
                pass

        # Fallback: simple face detection → "neutral"
        if self.haar is not None:
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            faces = self.haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))
            if len(faces) > 0:
                return "neutral", 0.8

        return None, 0.0

# -----------------------------
# GUI App
# -----------------------------
class BaymaxApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BAYMAX — JARVIS AI Medical Assistant")
        self.root.geometry("980x700")

        self.speak_responses = SPEAK_RESPONSES_DEFAULT

        # camera / emotion
        self.enable_camera = ENABLE_CAMERA_DEFAULT
        self.camera_thread = None
        self.camera_stop_event = threading.Event()
        self.emotion_detector = EmotionDetector()
        self.last_emotion = None
        self.emotion_lock = threading.Lock()

        # chat runtime
        self.current_thread = None
        self.cancel_event = threading.Event()

        # ---------- Menu ----------
        men = tk.Menu(root)
        root.config(menu=men)

        file_menu = tk.Menu(men, tearoff=0)
        men.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save conversation (JSON)", command=self.save_chat)
        file_menu.add_command(label="Export as text", command=self.export_plain_text)
        file_menu.add_separator()
        file_menu.add_command(label="Clear chat", command=self.clear_chat)
        file_menu.add_command(label="Exit", command=self.on_exit)

        men.add_command(label="Settings", command=self.open_settings)

        # ---------- Header ----------
        header = tk.Frame(root, bg="#0f1720")
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="BAYMAX — JARVIS AI Medical Assistant",
            font=("Consolas", 16, "bold"),
            fg="#00FFAB",
            bg="#0f1720",
        ).pack(side=tk.LEFT, padx=10, pady=8)

        wear_btn = tk.Button(header, text="Fetch Wearable Data", command=self.fetch_wearable)
        wear_btn.pack(side=tk.RIGHT, padx=10)

        # ---------- Chat window ----------
        self.chat_window = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#07080a",
            fg="#00FFAB",
            font=("Consolas", 12),
        )
        self.chat_window.pack(padx=12, pady=(6, 8), fill=tk.BOTH, expand=True)

        # ---------- Status bar ----------
        status_frame = tk.Frame(root)
        status_frame.pack(fill=tk.X, padx=12, pady=(0, 4))

        self.emotion_label = tk.Label(status_frame, text="Emotion: N/A", anchor=tk.W)
        self.emotion_label.pack(side=tk.LEFT)

        self.model_status_label = tk.Label(status_frame, text="Model: checking...", anchor=tk.E)
        self.model_status_label.pack(side=tk.RIGHT)

        # ---------- Entry area ----------
        entry_frame = tk.Frame(root, bg="#0f1720")
        entry_frame.pack(fill=tk.X, padx=12, pady=(4, 12))

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

        # ---------- Welcome ----------
        self.safe_insert(
            "👋 Hi! I'm BAYMAX.\n"
            "I can give general medical information and wellness tips.\n"
            "I am NOT a doctor and cannot diagnose or treat.\n"
            "If you ever feel it's an emergency, call your local emergency number immediately.\n\n"
        )

        # start camera if enabled
        if self.enable_camera and cv2 is not None:
            self.start_camera_thread()

        # periodic status updates
        self.root.after(1000, self.update_status_labels)

    # ------------- UI helpers -------------
    def _append_text(self, text: str):
        self.chat_window.config(state=tk.NORMAL)
        self.chat_window.insert(tk.END, text)
        self.chat_window.config(state=tk.DISABLED)
        self.chat_window.yview(tk.END)

    def safe_insert(self, text: str):
        self.root.after(0, self._append_text, text)

    # ------------- Status updating -------------
    def update_status_labels(self):
        # model
        running = is_ollama_running()
        self.model_status_label.config(text="Ollama: UP" if running else "Ollama: DOWN")

        # emotion
        with self.emotion_lock:
            if self.last_emotion:
                label, score = self.last_emotion
                self.emotion_label.config(text=f"Emotion: {label} ({score:.2f})")
            else:
                self.emotion_label.config(text="Emotion: N/A")

        self.root.after(2000, self.update_status_labels)

    # ------------- Camera control -------------
    def start_camera_thread(self):
        if cv2 is None:
            self.safe_insert("❌ OpenCV not installed — camera disabled.\n\n")
            return
        if self.camera_thread and self.camera_thread.is_alive():
            return
        self.camera_stop_event.clear()
        self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.camera_thread.start()
        self.safe_insert("📷 Camera emotion polling started.\n\n")

    def stop_camera_thread(self):
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_stop_event.set()
            self.camera_thread.join(timeout=1.5)
            self.safe_insert("📷 Camera emotion polling stopped.\n\n")

    def _camera_loop(self):
        cap = try_open_camera()
        if not cap:
            self.safe_insert("❌ Could not open webcam (no camera detected or permission denied).\n\n")
            return

        try:
            while not self.camera_stop_event.is_set():
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.5)
                    continue

                label, score = self.emotion_detector.detect(frame)
                if label is not None:
                    with self.emotion_lock:
                        self.last_emotion = (label, score)

                    # optional gentle suggestion on stress/low mood
                    if label in ("sad", "angry", "fear", "disgust") and score > 0.6:
                        self.safe_insert(
                            f"💡 You seem '{label}' ({score:.2f}). "
                            "Consider a short break, some water, or a breathing exercise.\n\n"
                        )

                time.sleep(EMOTION_POLL_INTERVAL)
        except Exception as e:
            self.safe_insert(f"❌ Camera loop error: {e}\n\n")
        finally:
            try:
                cap.release()
            except Exception:
                pass

    # ------------- Events -------------
    def on_send(self, event=None):
        txt = self.user_entry.get().strip()
        if not txt:
            return
        self.user_entry.delete(0, tk.END)
        self.submit_user_message(txt, source="text")

    def on_speak(self):
        if sr is None:
            self.safe_insert("❌ SpeechRecognition not installed. Voice not available.\n\n")
            return
        threading.Thread(target=self.listen_and_submit, daemon=True).start()

    def on_cancel(self):
        self.cancel_event.set()
        self.safe_insert("⏹️ Cancel requested. Stopping current response...\n\n")

    def on_exit(self):
        self.stop_camera_thread()
        try:
            self.root.quit()
        except Exception:
            pass

    # ------------- Chat flow -------------
    def set_busy(self, busy: bool):
        self.cancel_btn.config(state=tk.NORMAL if busy else tk.DISABLED)

    def submit_user_message(self, text, source="text"):
        if self.current_thread and self.current_thread.is_alive():
            self.safe_insert("⚠️ A response is already in progress. Click 'Cancel' to stop it.\n\n")
            return

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with history_lock:
            conversation_history.append({"role": "user", "text": text, "time": ts})

        self.safe_insert(f"🧑 You ({source}): {text}\n")

        # emergency detection
        is_em, kw = detect_emergency(text)
        if is_em:
            region_contacts = EMERGENCY_CONTACTS.get(DEFAULT_CONTACT_REGION, EMERGENCY_CONTACTS["global"])
            police_num = region_contacts.get("police", "112")
            ambulance_num = region_contacts.get("ambulance", "112")
            note = region_contacts.get("note", "")

            emergency_msg = (
                f"⚠️ I detected possible emergency-related symptoms (keyword: '{kw}').\n\n"
                f"If this feels severe or life-threatening, call your local emergency services immediately.\n"
                f"India quick numbers (default): Police/All-Emergency: {police_num}, Ambulance: {ambulance_num}.\n"
                f"{note}\n\n"
                "I can share general first-aid steps, but this does NOT replace real medical help."
            )

            ts2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with history_lock:
                conversation_history.append({"role": "assistant", "text": emergency_msg, "time": ts2})

            self.safe_insert(f"🤖 BAYMAX: {emergency_msg}\n\n")

            if self.speak_responses:
                threading.Thread(target=speak_text, args=(emergency_msg,), daemon=True).start()
            return

        self.cancel_event.clear()
        self.set_busy(True)
        self.safe_insert("🤖 BAYMAX: ")

        def worker(user_text: str):
            resp_accum = []
            error_text = None
            try:
                for chunk in generate_stream(user_text):
                    if self.cancel_event.is_set():
                        break
                    if chunk:
                        resp_accum.append(chunk)
                        self.safe_insert(chunk)
                self.safe_insert("\n\n")
            except requests.RequestException as e:
                error_text = f"Error contacting model: {e}"
            except Exception as e:
                error_text = f"Unexpected error: {e}"
            finally:
                final_text = "".join(resp_accum)
                if self.cancel_event.is_set():
                    final_text += "\n(Generation canceled by user.)"
                if error_text:
                    self.safe_insert(error_text + "\n\n")
                    final_text = error_text

                ts3 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with history_lock:
                    conversation_history.append({
                        "role": "assistant",
                        "text": final_text,
                        "time": ts3,
                    })

                if self.speak_responses and final_text and not self.cancel_event.is_set():
                    threading.Thread(target=speak_text, args=(final_text,), daemon=True).start()

                self.set_busy(False)

        self.current_thread = threading.Thread(target=worker, args=(text,), daemon=True)
        self.current_thread.start()

    # ------------- Voice -------------
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

    # ------------- Wearable mock -------------
    def fetch_wearable(self):
        data = {
            "hr": 72,
            "steps_today": 4200,
            "sleep_hours": 6.5,
            "last_sync": datetime.utcnow().isoformat() + "Z",
        }
        self.safe_insert(f"📟 Wearable: {json.dumps(data, indent=0)}\n\n")

    # ------------- Chat saving / clearing -------------
    def clear_chat(self):
        if messagebox.askyesno("Clear chat", "Clear conversation history?"):
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
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                for msg in conversation_history:
                    f.write(f"[{msg['time']}] {msg['role'].upper()}: {msg['text']}\n")
            messagebox.showinfo("Exported", f"Plain text exported to {path}")

    # ------------- Settings -------------
    def open_settings(self):
        global REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT, MODEL_NAME, API_GENERATE, DEFAULT_CONTACT_REGION

        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("520x420")

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

        tk.Label(win, text="Emergency region:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        region_var = tk.StringVar(value=DEFAULT_CONTACT_REGION)
        tk.OptionMenu(win, region_var, "india", "global", "us_uk").pack(anchor=tk.W, padx=10)

        cam_var = tk.BooleanVar(value=self.enable_camera)
        tk.Checkbutton(win, text="Enable camera emotion polling", variable=cam_var).pack(
            anchor=tk.W, padx=10, pady=(10, 0)
        )

        speak_var = tk.BooleanVar(value=self.speak_responses)
        tk.Checkbutton(win, text="Speak responses (TTS)", variable=speak_var).pack(
            anchor=tk.W, padx=10, pady=(10, 0)
        )

        def save_and_close():
            nonlocal region_var, cam_var, speak_var
            global API_GENERATE, MODEL_NAME, REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT, DEFAULT_CONTACT_REGION

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

            DEFAULT_CONTACT_REGION = region_var.get()
            self.speak_responses = bool(speak_var.get())

            new_cam = bool(cam_var.get())
            if new_cam and not self.enable_camera:
                self.enable_camera = True
                self.start_camera_thread()
            elif not new_cam and self.enable_camera:
                self.enable_camera = False
                self.stop_camera_thread()

            win.destroy()
            messagebox.showinfo("Settings", "Settings saved. Endpoint changes may require restart.")

        tk.Button(win, text="Save", command=save_and_close).pack(pady=12)

# -----------------------------
# Main
# -----------------------------
def main():
    ok = ensure_ollama_running(timeout=OLLAMA_START_WAIT)
    if not ok:
        print("Ollama not running and could not be auto-started.")
        try:
            proceed = messagebox.askyesno(
                "Ollama not running",
                "Ollama server is not running and could not be started.\n"
                "Continue anyway? (You must point to some other working endpoint in Settings.)",
            )
        except Exception:
            proceed = False
        if not proceed:
            return

    init_tts()
    preload_model()

    root = tk.Tk()
    app = BaymaxApp(root)
    try:
        root.mainloop()
    finally:
        app.stop_camera_thread()

if __name__ == "__main__":
    main()
