"""Tests for the GPU stats helper."""

from unittest.mock import patch


def test_get_gpu_stats_no_cuda() -> None:
    """Returns empty list when CUDA is unavailable."""
    with patch("doppelganger.tts.gpu.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = False

        from doppelganger.tts.gpu import get_gpu_stats

        result = get_gpu_stats()
        assert result == []


def test_get_gpu_stats_single_gpu() -> None:
    """Returns VRAM stats for a single GPU."""
    with patch("doppelganger.tts.gpu.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.get_device_name.return_value = "RTX 3090 Ti"
        # mem_get_info returns (free, total)
        total = 24 * 1024 * 1024 * 1024  # 24 GB
        free = 20 * 1024 * 1024 * 1024  # 20 GB
        mock_torch.cuda.mem_get_info.return_value = (free, total)

        from doppelganger.tts.gpu import get_gpu_stats

        result = get_gpu_stats()
        assert len(result) == 1

        gpu = result[0]
        assert gpu["index"] == 0
        assert gpu["name"] == "RTX 3090 Ti"
        assert gpu["vram_total_mb"] == 24576
        assert gpu["vram_used_mb"] == 4096
        assert gpu["vram_percent"] > 0


def test_get_gpu_stats_multiple_gpus() -> None:
    """Returns stats for each visible GPU."""
    with patch("doppelganger.tts.gpu.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 2
        mock_torch.cuda.get_device_name.side_effect = ["GT 1030", "RTX 3090 Ti"]

        total_small = 2 * 1024 * 1024 * 1024
        total_big = 24 * 1024 * 1024 * 1024
        mock_torch.cuda.mem_get_info.side_effect = [
            (total_small, total_small),  # GT 1030: all free
            (total_big // 2, total_big),  # RTX 3090: half used
        ]

        from doppelganger.tts.gpu import get_gpu_stats

        result = get_gpu_stats()
        assert len(result) == 2
        assert result[0]["name"] == "GT 1030"
        assert result[1]["name"] == "RTX 3090 Ti"


def test_get_gpu_stats_pynvml_failure_graceful() -> None:
    """Falls back gracefully when pynvml is unavailable."""
    with patch("doppelganger.tts.gpu.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.get_device_name.return_value = "RTX 3090 Ti"
        total = 24 * 1024 * 1024 * 1024
        mock_torch.cuda.mem_get_info.return_value = (total, total)

        from doppelganger.tts.gpu import get_gpu_stats

        # pynvml import will fail naturally in test env
        result = get_gpu_stats()
        assert len(result) == 1
        assert result[0]["utilization_percent"] is None
        assert result[0]["temperature_c"] is None
