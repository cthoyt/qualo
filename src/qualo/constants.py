"""Constants for QUALO."""

from pathlib import Path

__all__ = [
    "HERE",
    "ROOT",
]

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent.resolve()
