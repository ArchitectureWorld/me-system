"""One-click, Docker-first acceptance experience for ME-System."""

from .contracts import AcceptanceCheck, AcceptanceReport, CheckStatus
from .renderer import render_report_html

__all__ = [
    "AcceptanceCheck",
    "AcceptanceReport",
    "CheckStatus",
    "render_report_html",
]
