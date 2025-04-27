import time
import traceback
import logging
import sys
import os
import cv2
import requests


from utils import load_config, download_image, run_inference, send_telegram_message, send_log_message


CONFIG_PATH = '/etc/concierge/config.yaml'
DEFAULT_MODEL_URL = "https://huggingface.co/.../yolov8n_person.onnx"
DEFAULT_MODEL_PATH = "/root/concierge/yolov8n_person.onnx"


def ensure_model_exists(model_path=DEFAULT_MODEL_PATH, model_url=DEFAULT_MODEL_URL):
    """Download the YOLO model if missing."""
    if not os.path.isfile(model_path):
        print(f"Model not found at {model_path}. Downloading...")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        response = requests.get(model_url, stream=True)
        response.raise_for_status()
        with open(model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("✅ Model downloaded successfully.")

def setup_logging():
    """Configure logging."""
    logger = logging.getLogger("concierge")
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))

    logger.addHandler(handler)
    return logger


def main():
    logger = setup_logging()

    config = load_config(CONFIG_PATH)

    model_path = config.get('model_path', DEFAULT_MODEL_PATH)
    model_url = config.get('model_url', DEFAULT_MODEL_URL)

    ensure_model_exists(model_path, model_url)

    snapshot_url = config.get('snapshot_url')
    model_path = config.get('model_path')
    confidence_threshold = config.get('confidence_threshold', 0.5)
    check_interval = config.get('check_interval_seconds', 60)
    debug_mode = config.get('DEBUG', False)

    logger.info("Concierge started.")
    logger.info(f"Snapshot URL: {snapshot_url}")
    logger.info(f"Model path: {model_path}")

    while True:
        try:
            logger.debug("Downloading snapshot...")
            img = download_image(snapshot_url)

            logger.debug("Running inference...")
            boxes = run_inference(img, model_path, confidence_threshold)

            if boxes:
                logger.info(f"Detected {len(boxes)} person(s). Marking image...")
                for box in boxes:
                    cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)

                send_telegram_message(config, img, text="arriving somebody")
                logger.info("Notification sent via Telegram.")
            else:
                logger.debug("No person detected.")

        except Exception as e:
            err_message = f"Concierge ERROR:\n{traceback.format_exc()}"
            logger.error(err_message)

            if debug_mode:
                try:
                    send_log_message(config, err_message)
                except Exception as telegram_error:
                    logger.error(f"Failed to send debug log to Telegram: {telegram_error}")

        time.sleep(check_interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nConcierge stopped by user.")
