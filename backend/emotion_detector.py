import base64
import numpy as np
import cv2
import platform

# Optional imports for facial analysis
try:
    from fer import FER
except Exception:
    FER = None

class EmotionDetector:
    def __init__(self):
        self.detector = None
        self.haar = None

        if FER is not None:
            try:
                # MTCNN is slow, disable it for real-time speed
                self.detector = FER(mtcnn=False)
            except Exception as e:
                print(f"[Emotion] FER init failed: {e}")
                self.detector = None

        try:
            # Haar cascades for face detection fallback
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.haar = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            print(f"[Emotion] Haar cascade init failed: {e}")
            self.haar = None

    def decode_base64_image(self, base64_str: str) -> np.ndarray:
        """
        Decodes a base64 data URL string into an OpenCV image (numpy array).
        """
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        
        img_bytes = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def detect_emotion(self, base64_str: str) -> dict:
        """
        Decodes base64 frame, detects face & emotion, and returns results.
        """
        try:
            frame = self.decode_base64_image(base64_str)
        except Exception as e:
            print(f"[Emotion] Base64 decoding failed: {e}")
            return {"emotion": "error", "score": 0.0, "face_box": None}

        if frame is None or frame.size == 0:
            return {"emotion": "no_frame", "score": 0.0, "face_box": None}

        h, w = frame.shape[:2]
        # Downscale for faster analysis
        small = cv2.resize(frame, (int(w * 0.5), int(h * 0.5)))

        # 1. Prefer FER if available
        if self.detector is not None:
            try:
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                data = self.detector.detect_emotions(rgb)
                if data:
                    box = data[0]["box"]  # [x, y, w, h] in downscaled space
                    scores = data[0]["emotions"]
                    label = max(scores, key=scores.get)
                    
                    # Scale box back to original frame size
                    original_box = [int(val * 2) for val in box]
                    return {
                        "emotion": label,
                        "score": float(scores[label]),
                        "face_box": original_box
                    }
            except Exception as e:
                print(f"[Emotion] FER detection error: {e}")

        # 2. Fallback: Haar Cascade face detection -> "neutral"
        if self.haar is not None:
            try:
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                faces = self.haar.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30)
                )
                if len(faces) > 0:
                    box = faces[0]  # [x, y, w, h] in downscaled
                    original_box = [int(val * 2) for val in box]
                    return {
                        "emotion": "neutral",
                        "score": 0.75,
                        "face_box": original_box
                    }
            except Exception as e:
                print(f"[Emotion] Haar detection error: {e}")

        return {"emotion": "none", "score": 0.0, "face_box": None}
