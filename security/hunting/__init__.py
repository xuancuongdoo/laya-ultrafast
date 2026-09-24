"""Hunting: offline audit playbooks + critics over a recon map."""

from .critics import critique
from .playbooks import PLAYBOOKS, run_all

__all__ = ["PLAYBOOKS", "critique", "run_all"]
