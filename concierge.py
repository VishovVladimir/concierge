import logging
import sys
import time
import traceback

import cv2

from utils import (
    load_config,
    download_image,
    run_inference,
    send_telegram_message,
    send_log_message,
    edit_telegram_message
)

CONFIG_PATH = '/etc/concierge/config.yaml'

def setup_logging():
    logger = logging.getLogger("concierge")
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))

    logger.addHandler(handler)
    return logger

def main():
    logger = setup_logging()

    config = load_config(CONFIG_PATH)

    snapshot_url = config.get('snapshot_url')
    confidence_threshold = config.get('confidence_threshold', 0.5)
    check_interval = config.get('check_interval_seconds', 2)
    debug_mode = config.get('DEBUG', False)

    logger.info("Concierge started.")
    logger.info(f"Snapshot URL: {snapshot_url}")

    last_detection_time = 0
    last_message_id = None
    last_chat_id = None

    while True:
        try:
            logger.debug("Downloading snapshot...")
            try:
                img = download_image(snapshot_url)
            except Exception as e:
                logger.error(f"Snapshot download failed: {e}")
                time.sleep(check_interval)
                continue

            logger.debug("Running inference...")
            boxes = run_inference(img, confidence_threshold)

            if boxes:
                logger.info(f"Detected {len(boxes)} person(s). Marking image...")
                for box in boxes:
                    cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)

                current_time = time.time()

                if last_detection_time and (current_time - last_detection_time < 60) and last_message_id:
                    logger.info("Editing previous Telegram message with new snapshot.")
                    try:
                        edit_telegram_message(config, img, last_chat_id, last_message_id)
                    except Exception as e:
                        logger.error(f"Failed to edit message: {e}")
                        logger.info("Trying to send new message instead.")
                        last_message_id, last_chat_id = send_telegram_message(config, img, text="arriving somebody")
                else:
                    logger.info("Sending new Telegram message.")
                    last_message_id, last_chat_id = send_telegram_message(config, img, text="arriving somebody")

                last_detection_time = current_time
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
