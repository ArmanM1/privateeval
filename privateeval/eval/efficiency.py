from __future__ import annotations

import statistics
import threading
import time
from dataclasses import dataclass
from typing import Callable

from privateeval.models.base import Generation


@dataclass
class Measurement:
    generation: Generation
    latency_ms: float
    peak_rss_mb: float | None


class _RssSampler:
    def __init__(self, poll_ms: int) -> None:
        self.poll_seconds = max(0.001, poll_ms / 1000)
        self.maximum: int | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        try:
            import psutil
        except ImportError:
            return
        process = psutil.Process()

        def sample() -> None:
            while not self._stop.is_set():
                rss = process.memory_info().rss
                self.maximum = rss if self.maximum is None else max(self.maximum, rss)
                self._stop.wait(self.poll_seconds)
            rss = process.memory_info().rss
            self.maximum = rss if self.maximum is None else max(self.maximum, rss)

        self._thread = threading.Thread(target=sample, daemon=True)
        self._thread.start()

    def stop(self) -> float | None:
        if self._thread is None:
            return None
        self._stop.set()
        self._thread.join(timeout=1)
        return None if self.maximum is None else self.maximum / (1024 * 1024)


def measure(call: Callable[[], Generation], poll_ms: int) -> Measurement:
    sampler = _RssSampler(poll_ms)
    sampler.start()
    started = time.perf_counter()
    generation = call()
    latency_ms = (time.perf_counter() - started) * 1000
    peak = sampler.stop()
    return Measurement(generation, latency_ms, peak)


def summarize_measurements(measurements: list[Measurement]) -> dict:
    latencies = [item.latency_ms for item in measurements]
    peaks = [item.peak_rss_mb for item in measurements if item.peak_rss_mb is not None]
    output = measurements[0].generation
    throughput = output.output_tokens / (statistics.median(latencies) / 1000) if latencies else 0.0
    return {
        "generation": output,
        "latency_ms": round(statistics.median(latencies), 3),
        "latency_repetitions_ms": [round(item, 3) for item in latencies],
        "peak_rss_mb": round(max(peaks), 3) if peaks else None,
        "output_tokens_per_second": round(throughput, 3),
    }
