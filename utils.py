import yaml
import requests
import numpy as np
import cv2
import onnxruntime as ort
from io import BytesIO


def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def download_image(url):
    """Download image from URL and return OpenCV image (BGR)."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    img_array = np.frombuffer(response.content, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img


def preprocess_image(img, input_size):
    """Resize and normalize image for ONNX model input."""
    img_resized = cv2.resize(img, (input_size, input_size))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_normalized = img_rgb.astype(np.float32) / 255.0
    img_transposed = np.transpose(img_normalized, (2, 0, 1))  # HWC to CHW
    img_input = np.expand_dims(img_transposed, axis=0)
    return img_input


def run_inference(img, model_path, confidence_threshold=0.5):
    """Run YOLO inference and return list of bounding boxes."""
    # Load model
    session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])

    # Preprocess
    input_size = session.get_inputs()[0].shape[2]  # assume (1,3,INPUT,INPUT)
    img_input = preprocess_image(img, input_size)

    # Inference
    outputs = session.run(None, {session.get_inputs()[0].name: img_input})
    outputs = np.squeeze(outputs[0])

    boxes = []
    img_h, img_w = img.shape[:2]

    for output in outputs:
        confidence = output[4]
        class_scores = output[5:]
        class_id = np.argmax(class_scores)
        class_confidence = class_scores[class_id]

        if confidence * class_confidence > confidence_threshold and class_id == 0:  # class_id==0 for 'person'
            # YOLO returns center x, center y, width, height normalized
            cx, cy, w, h = output[0:4]
            x1 = int((cx - w / 2) * img_w)
            y1 = int((cy - h / 2) * img_h)
            x2 = int((cx + w / 2) * img_w)
            y2 = int((cy + h / 2) * img_h)
            boxes.append((x1, y1, x2, y2))

    return boxes


def send_telegram_message(config, img, text=""):
    """Send photo and caption to Telegram chat."""
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
    """Send a debug text message to Telegram if DEBUG enabled."""
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
