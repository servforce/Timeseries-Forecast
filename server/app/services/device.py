from __future__ import annotations

from typing import Literal


Device = Literal["cuda", "cpu"]


def choose_device(prefer_cuda: bool = True) -> Device:
    """
    Auto-select inference/training device.

    Policy:
    - Prefer CUDA if available
    - Fallback to CPU
    """
    if prefer_cuda:
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
    return "cpu"

