"""GPU stats helper using torch.cuda and optional pynvml."""

from __future__ import annotations

import logging
from typing import Any

import torch

try:
    import pynvml  # type: ignore[import-untyped]
except ImportError:
    pynvml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def get_gpu_stats() -> list[dict[str, Any]]:
    """Return VRAM usage and optional utilization/temperature for each visible GPU."""
    if not torch.cuda.is_available():
        return []

    results: list[dict[str, Any]] = []
    device_count = torch.cuda.device_count()

    if pynvml is not None:
        try:
            pynvml.nvmlInit()
        except Exception:
            logger.debug("pynvml.nvmlInit() failed, skipping utilization/temp")

    for i in range(device_count):
        name = torch.cuda.get_device_name(i)
        free, total = torch.cuda.mem_get_info(i)
        used = total - free
        used_mb = used // (1024 * 1024)
        total_mb = total // (1024 * 1024)
        vram_percent = round((used / total) * 100, 1) if total > 0 else 0.0

        info: dict[str, Any] = {
            "index": i,
            "name": name,
            "vram_used_mb": used_mb,
            "vram_total_mb": total_mb,
            "vram_percent": vram_percent,
            "utilization_percent": None,
            "temperature_c": None,
        }

        if pynvml is not None:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                info["utilization_percent"] = float(util.gpu)

                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                info["temperature_c"] = temp

            except Exception:
                logger.debug("pynvml unavailable for GPU %d, skipping utilization/temp", i)

        results.append(info)

    return results
