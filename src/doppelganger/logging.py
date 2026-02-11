"""Logging configuration with colored output and third-party noise suppression."""

import logging

_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",  # cyan
    logging.INFO: "\033[32m",  # green
    logging.WARNING: "\033[33m",  # yellow
    logging.ERROR: "\033[31m",  # red
    logging.CRITICAL: "\033[1;31m",  # bold red
}
_RESET = "\033[0m"
_DIM = "\033[2m"

# noisy third-party loggers that only matter when something breaks
_NOISY_LOGGERS = [
    "discord",
    "chatterbox",
    "transformers",
    "torch",
    "diffusers",
    "httpx",
    "httpcore",
    "uvicorn.access",
]


class ColorFormatter(logging.Formatter):
    """Log formatter with ANSI colors and datetime."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with color-coded level and dim timestamp."""
        color = _LEVEL_COLORS.get(record.levelno, "")
        ts = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        return f"{_DIM}{ts}{_RESET} {color}{record.levelname:<8}{_RESET} {record.name} - {record.getMessage()}"


def setup_logging(*, debug: bool = False) -> None:
    """Configure root and project loggers with colored output."""
    log_level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.WARNING)
    logging.getLogger("doppelganger").setLevel(log_level)

    # transformers LlamaSdpaAttention fallback - remove when chatterbox updates
    logging.getLogger("transformers.models.llama.modeling_llama").setLevel(logging.ERROR)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
