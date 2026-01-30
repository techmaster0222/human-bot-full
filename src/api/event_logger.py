"""
Event Logger - Structured event logging to console and file
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EventLogger:
    """
    Event logger for capturing bot events.

    Features:
    - Console logging with colors
    - File logging (JSON or text format)
    - Log level filtering
    - Structured event format

    Usage:
        logger = EventLogger(log_file="logs/events.log", log_format="json")
        logger.log_event("session_start", {"session_id": "abc123"})
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "RESET": "\033[0m",  # Reset
    }

    def __init__(
        self,
        log_file: str | None = None,
        log_format: str = "json",
        log_level: str = "INFO",
        console_output: bool = True,
    ):
        """
        Initialize event logger.

        Args:
            log_file: Optional log file path
            log_format: "json" or "text"
            log_level: Minimum log level ("DEBUG", "INFO", "WARNING", "ERROR")
            console_output: Whether to print to console
        """
        self.log_format = log_format
        self.log_file = log_file
        self.log_level = log_level
        self.console_output = console_output

        # Create logs directory if needed
        if log_file:
            log_path = Path(log_file).parent
            log_path.mkdir(parents=True, exist_ok=True)

    def _should_log(self, level: str) -> bool:
        """Check if level should be logged"""
        levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        return levels.get(level, 1) >= levels.get(self.log_level, 1)

    def _format_console(self, event: dict[str, Any]) -> str:
        """Format event for console output"""
        level = event.get("level", "INFO")
        event_type = event.get("type", "unknown")
        timestamp = event.get("timestamp", "")[:19]  # Truncate to seconds
        data = event.get("data", {})

        color = self.COLORS.get(level, "")
        reset = self.COLORS["RESET"]

        # Build data string (truncate long values)
        data_parts = []
        for k, v in data.items():
            v_str = str(v)
            if len(v_str) > 50:
                v_str = v_str[:47] + "..."
            data_parts.append(f"{k}={v_str}")
        data_str = ", ".join(data_parts)

        return f"{color}[{level}]{reset} {timestamp} | {event_type} | {data_str}"

    def _format_json(self, event: dict[str, Any]) -> str:
        """Format event as JSON"""
        return json.dumps(event, default=str)

    def _format_text(self, event: dict[str, Any]) -> str:
        """Format event as text"""
        level = event.get("level", "INFO")
        event_type = event.get("type", "unknown")
        timestamp = event.get("timestamp", "")
        data = json.dumps(event.get("data", {}), default=str)
        return f"[{level}] {timestamp} | {event_type}: {data}"

    def _write_log(self, event: dict[str, Any]) -> None:
        """Write log message"""
        # Console output
        if self.console_output:
            print(self._format_console(event))

        # File output
        if self.log_file:
            if self.log_format == "json":
                line = self._format_json(event)
            else:
                line = self._format_text(event)

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def log_event(
        self, event_type: str, data: dict[str, Any], level: str = "INFO", timestamp: str = None
    ) -> dict[str, Any]:
        """
        Log an event.

        Args:
            event_type: Event type (e.g., "session_start", "click")
            data: Event data dictionary
            level: Log level
            timestamp: Optional timestamp (defaults to now)

        Returns:
            The event dictionary
        """
        if not self._should_log(level):
            return {}

        event = {
            "type": event_type,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "data": data,
            "level": level,
        }

        self._write_log(event)
        return event

    # ============== Convenience Methods ==============

    def log_session_start(
        self,
        session_id: str,
        profile_id: str,
        device: str = "unknown",
        target_url: str = None,
        proxy: str = None,
        country: str = None,
    ) -> dict[str, Any]:
        """Log session start"""
        return self.log_event(
            "session_start",
            {
                "session_id": session_id,
                "profile_id": profile_id,
                "device": device,
                "target_url": target_url,
                "proxy": proxy,
                "country": country,
            },
        )

    def log_session_end(
        self, session_id: str, success: bool, duration: float, error: str = None
    ) -> dict[str, Any]:
        """Log session end"""
        return self.log_event(
            "session_end",
            {"session_id": session_id, "success": success, "duration": duration, "error": error},
            level="INFO" if success else "WARNING",
        )

    def log_navigation(
        self, session_id: str, url: str, success: bool = True, latency_ms: int = None
    ) -> dict[str, Any]:
        """Log navigation event"""
        return self.log_event(
            "navigation",
            {"session_id": session_id, "url": url, "success": success, "latency_ms": latency_ms},
        )

    def log_click(self, session_id: str, element: str = None, url: str = None) -> dict[str, Any]:
        """Log click event"""
        return self.log_event("click", {"session_id": session_id, "element": element, "url": url})

    def log_scroll(self, session_id: str, direction: str, amount: int = None) -> dict[str, Any]:
        """Log scroll event"""
        return self.log_event(
            "scroll", {"session_id": session_id, "direction": direction, "amount": amount}
        )

    def log_proxy_assigned(
        self, session_id: str, proxy: str, country: str = None
    ) -> dict[str, Any]:
        """Log proxy assignment"""
        return self.log_event(
            "proxy_assigned", {"session_id": session_id, "proxy": proxy, "country": country}
        )

    def log_ip_rotation(
        self, old_ip: str = None, new_ip: str = None, reason: str = None
    ) -> dict[str, Any]:
        """Log IP rotation"""
        return self.log_event("ip_rotation", {"old_ip": old_ip, "new_ip": new_ip, "reason": reason})

    def log_error(
        self, session_id: str = None, error: str = None, error_type: str = None
    ) -> dict[str, Any]:
        """Log error"""
        return self.log_event(
            "error",
            {"session_id": session_id, "error": error, "error_type": error_type},
            level="ERROR",
        )

    def log_warning(
        self, message: str, session_id: str = None, data: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Log warning"""
        return self.log_event(
            "warning",
            {"session_id": session_id, "message": message, **(data or {})},
            level="WARNING",
        )
