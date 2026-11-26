"""File d'attente : envoie les SMS un par un, avec pause et retries."""
import threading
import time
from datetime import datetime, timedelta, timezone

import config
import sender
import storage

_stop = threading.Event()
_thread: threading.Thread | None = None


def _loop() -> None:
    pause = 60.0 / max(config.RATE_LIMIT_PER_MIN, 1)
    while not _stop.is_set():
        sms = storage.next_pending()
        if not sms:
            _stop.wait(1)
            continue

        try:
            sender.send(sms["number"], sms["message"])
            storage.mark_sent(sms["id"])
        except Exception as e:  # noqa: BLE001
            if sms["attempts"] + 1 >= config.MAX_RETRIES:
                storage.mark_failed(sms["id"], str(e))
            else:
                retry_at = datetime.now(timezone.utc) + timedelta(
                    seconds=config.RETRY_DELAY_SEC
                )
                storage.mark_retry(
                    sms["id"], str(e), retry_at.isoformat(timespec="seconds")
                )
        _stop.wait(pause)  # protège la SIM


def start() -> None:
    global _thread
    _stop.clear()
    _thread = threading.Thread(target=_loop, daemon=True, name="sms-worker")
    _thread.start()


def stop() -> None:
    _stop.set()
    if _thread:
        _thread.join(timeout=5)
