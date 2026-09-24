from __future__ import annotations

import math
import os
import time
from typing import Any

from .base import Generation, ModelAdapter


def _tensor_bytes(value: Any) -> int:
    if hasattr(value, "numel") and hasattr(value, "element_size"):
        try:
            return int(value.numel() * value.element_size())
        except Exception:
            return 0
    if isinstance(value, dict):
        return sum(_tensor_bytes(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return sum(_tensor_bytes(item) for item in value)
    return 0


class TransformersAdapter(ModelAdapter):
    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.model = None
        self.tokenizer = None
        self._model_size_mb = 0.0

    def load(self) -> None:
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as error:
            raise RuntimeError(
                "The measured local run requires the locked optional dependencies. "
                "Install requirements-lock.txt first."
            ) from error

        started = time.perf_counter()
        threads = min(8, max(1, os.cpu_count() or 1))
        torch.set_num_threads(threads)
        model_name = self.config["model_name"]
        revision = self.config.get("revision", "main")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, revision=revision)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            revision=revision,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=False,
        )
        self.model.eval()
        if self.config.get("quantization") == "dynamic-int8":
            self.model = torch.ao.quantization.quantize_dynamic(
                self.model, {torch.nn.Linear}, dtype=torch.qint8, inplace=False
            )
            self.model.eval()
        try:
            state = self.model.state_dict()
            self._model_size_mb = _tensor_bytes(state) / (1024 * 1024)
        except Exception:
            self._model_size_mb = float(self.model.get_memory_footprint()) / (1024 * 1024)
        self.load_time_ms = (time.perf_counter() - started) * 1000

    def summarize(self, text: str) -> Generation:
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Adapter must be loaded before generation")
        import torch

        prompt = (
            "Summarize the following public document in 45 to 90 words. State the main "
            "action and material constraints. Do not invent facts or repeat contact details.\n\n"
            + text
        )
        encoded = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        with torch.inference_mode():
            output = self.model.generate(
                **encoded,
                max_new_tokens=int(self.config.get("max_new_tokens", 72)),
                min_new_tokens=18,
                do_sample=False,
                num_beams=1,
                return_dict_in_generate=True,
                output_scores=True,
            )
        sequence = output.sequences[0]
        text_out = self.tokenizer.decode(sequence, skip_special_tokens=True).strip()
        entropies: list[float] = []
        vocabulary = None
        for scores in output.scores:
            logits = scores[0].float()
            probabilities = torch.softmax(logits, dim=-1)
            entropy = -(probabilities * torch.log(probabilities + 1e-12)).sum().item()
            vocabulary = logits.numel()
            entropies.append(entropy)
        confidence = None
        if entropies and vocabulary:
            confidence = 1.0 - sum(entropies) / len(entropies) / math.log(vocabulary)
            confidence = round(max(0.0, min(1.0, confidence)), 4)
        return Generation(
            text=text_out,
            input_tokens=int(encoded["input_ids"].shape[-1]),
            output_tokens=int(sequence.shape[-1]),
            confidence=confidence,
            metadata={
                "model_name": self.config["model_name"],
                "revision": self.config.get("revision", "main"),
                "quantization": self.config.get("quantization", "none"),
                "deterministic": True,
            },
        )

    def model_size_mb(self) -> float:
        return round(self._model_size_mb, 3)

    def close(self) -> None:
        self.model = None
        self.tokenizer = None
        try:
            import gc
            gc.collect()
        except Exception:
            pass
