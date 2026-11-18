"""Move code from the remove.bg v1.0 API to a compatible endpoint."""
from .client import ApiError, RemoveBgClient, Result
from .rewrite import rewrite
from .scan import Finding, scan

__all__ = ["ApiError", "RemoveBgClient", "Result", "Finding", "scan", "rewrite"]
__version__ = "0.1.0"
