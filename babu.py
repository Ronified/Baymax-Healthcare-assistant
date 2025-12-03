
import sys, platform, importlib
print("Python:", sys.version.splitlines()[0])
print("OS:", platform.system(), platform.release())
for pkg in ("cv2","fer","mediapipe","numpy"):
    try:
        m = importlib.import_module(pkg)
        print(pkg, "OK")
    except Exception as e:
        print(pkg, "MISSING or failed to import:", e)
PY
