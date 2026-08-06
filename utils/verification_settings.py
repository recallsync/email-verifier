"""Verification settings passed to check_email."""

from dataclasses import dataclass
from typing import Any


@dataclass
class VerificationSettings:
    timeout_seconds: int = 15
    retry_count: int = 1
    smtp_helo_domain: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VerificationSettings":
        if not data:
            return cls()
        return cls(
            timeout_seconds=int(data.get("timeout_seconds", 15)),
            retry_count=int(data.get("retry_count", 1)),
            smtp_helo_domain=str(data.get("smtp_helo_domain") or ""),
        )

    @property
    def sender_domain(self) -> str:
        domain = (self.smtp_helo_domain or "").strip()
        return domain if domain else "gmail.com"

    @property
    def sender_email(self) -> str:
        return f"verify@{self.sender_domain}"
