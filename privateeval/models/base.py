from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Generation:
    text: str
    input_tokens: int
    output_tokens: int
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelAdapter(ABC):
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.id = config["id"]
        self.label = config["label"]
        self.load_time_ms = 0.0

    @abstractmethod
    def load(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def summarize(self, text: str) -> Generation:
        raise NotImplementedError

    @abstractmethod
    def model_size_mb(self) -> float:
        raise NotImplementedError

    def close(self) -> None:
        return None

