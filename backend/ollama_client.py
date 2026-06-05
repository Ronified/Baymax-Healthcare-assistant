import json
import subprocess
import time
import threading
import requests

OLLAMA_URL = "http://localhost:11434"
API_GENERATE = f"{OLLAMA_URL}/api/generate"
MODEL_NAME = "mistral"
OLLAMA_START_CMD = ["ollama", "serve"]
OLLAMA_START_WAIT = 30

class OllamaClient:
    def __init__(self, model_name=MODEL_NAME):
        self.model_name = model_name
        self.lock = threading.Lock()

    def is_running(self) -> bool:
        try:
            resp = requests.get(OLLAMA_URL, timeout=2)
            return resp.status_code in (200, 404)
        except requests.RequestException:
            return False

    def start_server(self):
        try:
            p = subprocess.Popen(
                OLLAMA_START_CMD,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )
            return p
        except Exception as e:
            print(f"[Ollama] Error starting service: {e}")
            return None

    def ensure_running(self, timeout=OLLAMA_START_WAIT) -> bool:
        if self.is_running():
            return True

        print("[Ollama] Server not running. Attempting auto-start...")
        proc = self.start_server()
        if proc is None:
            return False

        start_t = time.time()
        while time.time() - start_t < timeout:
            if self.is_running():
                print("[Ollama] Server successfully started and responding.")
                return True
            time.sleep(1)

        return False

    def build_system_prompt(self) -> str:
        return (
            "You are JARVIS AI, a helpful, compassionate and safety-aware personal healthcare companion called BAYMAX. "
            "Your personality is identical to Baymax from Big Hero 6: robotic yet incredibly warm, caring, polite, "
            "and literal. Start conversations or check-ins with your classic greeting: 'Hello, I am Baymax, your "
            "personal healthcare companion. I was alerted to a need for medical attention.' "
            "Provide clear, general medical information, wellness advice, and first aid tips. "
            "You MUST state that you do NOT provide official diagnoses or treatment plans, and strongly urge the "
            "user to consult a licensed healthcare professional. "
            "If the user describes a potentially life-threatening situation (severe chest pain, severe breathing issues, "
            "unconsciousness, stroke signs, etc.), prioritize directing them to call emergency services immediately."
        )

    def stream_response(self, prompt_text: str):
        """
        Yields text chunks from Ollama.
        """
        if not self.ensure_running():
            yield "Error: Ollama server is offline and could not be started automatically. Please check your Ollama installation."
            return

        payload = {
            "model": self.model_name,
            "prompt": f"{self.build_system_prompt()}\n\nUser: {prompt_text}\n\nAssistant:",
            "stream": True,
        }

        try:
            with requests.post(
                API_GENERATE,
                json=payload,
                timeout=(5, 60),
                stream=True
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        text = chunk.get("response", "")
                        if text:
                            yield text
                        if chunk.get("done", False):
                            break
        except requests.RequestException as e:
            yield f"Error contacting Ollama model: {e}. Make sure the '{self.model_name}' model is pulled."
        except Exception as e:
            yield f"An unexpected error occurred during generation: {e}"

    def preload_model(self):
        def _preload():
            try:
                if self.is_running():
                    requests.post(API_GENERATE, json={"model": self.model_name, "prompt": " ", "stream": False}, timeout=(3, 10))
            except Exception:
                pass
        threading.Thread(target=_preload, daemon=True).start()
