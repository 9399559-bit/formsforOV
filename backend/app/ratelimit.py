"""Слой 1 защиты от спама: in-memory sliding-window rate-limit по IP.

Хранилище — в памяти процесса (перезапуск обнуляет счётчики, это приемлемо).
Не заменяет клиентский cooldown (слой 2) — оба слоя работают параллельно.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Optional


class SlidingWindowRateLimiter:
    """Считает принятые заявки по IP в двух скользящих окнах (10 мин и 60 мин).

    Хранит timestamps принятых заявок на каждый IP, чистит всё старше большего
    окна при каждом обращении — память не растёт. Потокобезопасен (lock).
    """

    WINDOW_10MIN_SECONDS = 600
    WINDOW_1H_SECONDS = 3600

    def __init__(self, limit_10min: int, limit_1h: int) -> None:
        self._limit_10min = limit_10min
        self._limit_1h = limit_1h
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> None:
        bucket = self._hits[key]
        cutoff = now - self.WINDOW_1H_SECONDS
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if not bucket:
            # Не держим пустые ключи — иначе словарь растёт по числу уникальных IP.
            self._hits.pop(key, None)

    def is_allowed(self, key: str, now: Optional[float] = None) -> bool:
        """True, если по этому IP ещё можно принять заявку в обоих окнах."""
        if now is None:
            now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            bucket = self._hits.get(key)
            if not bucket:
                return True
            if len(bucket) >= self._limit_1h:
                return False
            cutoff_10min = now - self.WINDOW_10MIN_SECONDS
            count_10min = sum(1 for ts in bucket if ts > cutoff_10min)
            return count_10min < self._limit_10min

    def record(self, key: str, now: Optional[float] = None) -> None:
        """Фиксирует принятую заявку по IP (вызывать только после успеха)."""
        if now is None:
            now = time.monotonic()
        with self._lock:
            self._hits[key].append(now)
            self._prune(key, now)


def get_client_ip(request) -> str:
    """Реальный IP за nginx: первый из X-Forwarded-For → X-Real-IP → client.host.

    request.client.host за прокси даёт 127.0.0.1, поэтому сначала смотрим
    проксируемые заголовки, и только потом — прямой адрес соединения.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first

    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"
