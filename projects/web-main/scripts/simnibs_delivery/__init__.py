"""Standardized SimNIBS service-delivery contracts and report rendering."""

from .contract import ContractError, validate_delivery
from .render import render_report

__all__ = ["ContractError", "render_report", "validate_delivery"]
