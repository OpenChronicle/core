"""Structured file output service.

File layout: ``{base_dir}/{report_type}/{YYYYMMDD_HHMMSS}.json``
Latest pointer: ``{base_dir}/{report_type}/latest.json`` (plain copy, not symlink).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from openchronicle.core.domain.exceptions import ValidationError
from openchronicle.core.domain.time_utils import utc_now

_logger = logging.getLogger(__name__)

_REPORT_TYPE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}$")


class OutputManager:
    """Manage structured JSON report output with timestamped files."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)

    def save_report(self, report_type: str, data: dict[str, object]) -> Path:
        """Write *data* as timestamped JSON. Updates ``latest.json`` pointer.

        Returns the path to the written file.
        """
        self._validate_report_type(report_type)
        type_dir = self.base_dir / report_type
        type_dir.mkdir(parents=True, exist_ok=True)

        ts = utc_now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}.json"
        dest = type_dir / filename
        content = json.dumps(data, indent=2, default=str)
        dest.write_text(content, encoding="utf-8")

        # Update latest pointer (plain copy for Windows compat)
        latest = type_dir / "latest.json"
        latest.write_text(content, encoding="utf-8")

        _logger.info("Saved report: %s", dest)
        return dest

    def list_outputs(self, report_type: str) -> list[Path]:
        """List output files for *report_type*, newest first.

        Excludes ``latest.json``.
        """
        self._validate_report_type(report_type)
        type_dir = self.base_dir / report_type
        if not type_dir.is_dir():
            return []
        files = [f for f in type_dir.glob("*.json") if f.name != "latest.json"]
        files.sort(key=lambda p: p.name, reverse=True)
        return files

    def latest_output(self, report_type: str) -> Path | None:
        """Return path to ``latest.json`` for *report_type*, or None."""
        self._validate_report_type(report_type)
        latest = self.base_dir / report_type / "latest.json"
        return latest if latest.is_file() else None

    def cleanup(self, max_age_days: int) -> int:
        """Delete output files older than *max_age_days*. Returns count deleted.

        Preserves ``latest.json`` pointers.
        """
        if max_age_days < 1:
            raise ValidationError("max_age_days must be >= 1", code="INVALID_ARGUMENT")

        now = utc_now()
        deleted = 0
        if not self.base_dir.is_dir():
            return 0

        for type_dir in self.base_dir.iterdir():
            if not type_dir.is_dir():
                continue
            for f in type_dir.glob("*.json"):
                if f.name == "latest.json":
                    continue
                age_days = (now.timestamp() - f.stat().st_mtime) / 86400
                if age_days > max_age_days:
                    f.unlink()
                    deleted += 1
                    _logger.debug("Deleted old output: %s", f)

        _logger.info("Cleanup: deleted %d files older than %d days", deleted, max_age_days)
        return deleted

    @staticmethod
    def _validate_report_type(report_type: str) -> None:
        """Guard against path traversal and invalid names."""
        if not _REPORT_TYPE_RE.match(report_type):
            raise ValidationError(
                f"Invalid report_type: {report_type!r} (alphanumeric, dots, hyphens, underscores only)",
                code="INVALID_ARGUMENT",
            )
