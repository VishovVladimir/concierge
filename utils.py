import yaml
import requests
import numpy as np
import cv2
from io import BytesIO
from ultralytics import YOLO
import json

# === Global model variable ===
MODEL = YOLO('yolov8n.pt')

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def download_image(url):
    """Download image from URL and return OpenCV BGR image."""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        img_array = np.frombuffer(response.content, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        raise RuntimeError(f"Snapshot download failed: {e}")

def run_inference(img, confidence_threshold=0.5):
    """Run inference using YOLO model."""
    results = MODEL.predict(img, conf=confidence_threshold, verbose=False)
    boxes = []

    for result in results:
        for box, cls in zip(result.boxes.xyxy, result.boxes.cls):
            if int(cls) == 0:  # class 0 = person
                x1, y1, x2, y2 = map(int, box)
                boxes.append((x1, y1, x2, y2))

    return boxes

def send_telegram_message(config, img, text=""):
    """Send photo to Telegram and return message_id and chat_id."""
    bot_token = config['telegram_bot_token']
    chat_ids = config['notify_user_ids']

    _, img_encoded = cv2.imencode('.jpg', img)
    img_bytes = BytesIO(img_encoded.tobytes())

    message_id = None
    chat_id = None

    for chat in chat_ids:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        data = {
            "chat_id": chat,
            "caption": text,
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "Take a photo", "callback_data": "take_photo"}]]
            })
        }
        files = {"photo": ("image.jpg", img_bytes.getvalue())}

        try:
            response = requests.post(url, data=data, files=files, timeout=20)
            response.raise_for_status()
            resp_json = response.json()
            if resp_json.get("ok"):
                message_id = resp_json["result"]["message_id"]
                chat_id = resp_json["result"]["chat"]["id"]
        except Exception as e:
            print(f"Failed to send Telegram photo: {e}")

    return message_id, chat_id

def edit_telegram_message(config, img, chat_id, message_id):
    """Edit existing Telegram message with new photo."""
    bot_token = config['telegram_bot_token']

    _, img_encoded = cv2.imencode('.jpg', img)
    img_bytes = BytesIO(img_encoded.tobytes())

    url = f"https://api.telegram.org/bot{bot_token}/editMessageMedia"

    media_payload = {
        "type": "photo",
        "media": "attach://photo",
        "caption": "arriving somebody"
    }

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "media": json.dumps(media_payload)
    }

    files = {
        "photo": ("image.jpg", img_bytes.getvalue())
    }

    try:
        response = requests.post(url, data=data, files=files, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to edit Telegram message: {e}")

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

def handle_callback(config, callback_data, chat_id, message_id, raw_img):
    """Respond to Telegram 'Take a photo' button press, with access control."""
    bot_token = config['telegram_bot_token']
    allowed_users = config.get("notify_user_ids", [])

    if chat_id not in allowed_users:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": "Access denied."
        }
        try:
            requests.post(url, data=data, timeout=10)
        except Exception as e:
            print(f"Failed to send access denied message: {e}")
        return

    if callback_data == "take_photo":
        if raw_img is not None:
            _, img_encoded = cv2.imencode('.jpg', raw_img)
            img_bytes = BytesIO(img_encoded.tobytes())
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            data = {"chat_id": chat_id}
            files = {"photo": ("raw.jpg", img_bytes.getvalue())}
            try:
                requests.post(url, data=data, files=files, timeout=20)
            except Exception as e:
                print(f"Failed to send raw photo: {e}")
        else:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": "Please wait, processing."
            }
            try:
                requests.post(url, data=data, timeout=10)
            except Exception as e:
                print(f"Failed to send fallback message: {e}")
