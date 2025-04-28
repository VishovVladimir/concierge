import yaml
import requests
import numpy as np
import cv2
from io import BytesIO
from ultralytics import YOLO

# === Auto-load YOLO model once ===
MODEL = None

def load_config(path):
    """Load YAML config."""
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def load_model(model_path):
    """Load YOLO model (.pt file) once."""
    global MODEL
    if MODEL is None:
        MODEL = YOLO(model_path)

def download_image(url):
    """Download image from URL and return OpenCV BGR image."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    img_array = np.frombuffer(response.content, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img

def run_inference(img, confidence_threshold=0.5):
    """Run inference using YOLO model."""
    if MODEL is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")

    results = MODEL.predict(img, conf=confidence_threshold, verbose=False)
    boxes = []

    for result in results:
        for box, cls in zip(result.boxes.xyxy, result.boxes.cls):
            if int(cls) == 0:  # class 0 = person
                x1, y1, x2, y2 = map(int, box)
                boxes.append((x1, y1, x2, y2))

    return boxes

def send_telegram_message(config, img, text=""):
    """Send image and text to Telegram."""
    bot_token = config['telegram_bot_token']
    chat_ids = config['notify_user_ids']

    _, img_encoded = cv2.imencode('.jpg', img)
    img_bytes = BytesIO(img_encoded.tobytes())

    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        data = {"chat_id": chat_id, "caption": text}
        files = {"photo": ("image.jpg", img_bytes.getvalue())}

        try:
            response = requests.post(url, data=data, files=files, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send Telegram photo: {e}")

def send_log_message(config, log_text):
    """Send debug text logs to Telegram."""
    bot_token = config['telegram_bot_token']
    chat_ids = config['notify_user_ids']

    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": log_text,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send log: {e}")
