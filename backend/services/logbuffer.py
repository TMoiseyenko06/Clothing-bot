import logging
from collections import deque
from datetime import datetime, timezone

_buffer: deque = deque(maxlen=300)


class _BufferHandler(logging.Handler):
    def emit(self, record):
        try:
            _buffer.append({
                "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                "level": record.levelname,
                "msg": self.format(record),
            })
        except Exception:
            pass


def setup():
    handler = _BufferHandler()
    handler.setFormatter(logging.Formatter("%(name)s — %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def get_logs() -> list:
    return list(_buffer)
