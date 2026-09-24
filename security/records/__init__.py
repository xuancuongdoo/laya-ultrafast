"""Verified security records: hash-linked findings chain + report derivation.

Chain lives here so orchestration stays thin: orchestrator dispatches,
records prove. Import surface:
  from security.records import append, verify_chain, verify_finding
  from security.records import derive_report, validate_report
"""

from security.records.chain import GENESIS_PREV, REQUIRED, SEVERITIES, append, verify_chain, verify_finding
from security.records.reports import REQUIRED_REPORT_FIELDS, derive_report, validate_report

__all__ = [
    "GENESIS_PREV",
    "REQUIRED",
    "SEVERITIES",
    "REQUIRED_REPORT_FIELDS",
    "append",
    "derive_report",
    "validate_report",
    "verify_chain",
    "verify_finding",
]
