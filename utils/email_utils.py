"""
Email verification utilities with robust multi-layered approach
"""
import re
import time
import socket
import dns.resolver
import smtplib

from utils.verification_settings import VerificationSettings

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
DISPOSABLE_DOMAINS = {
    "mailinator.com",
    "10minutemail.com",
    "guerrillamail.com",
    "tempmail.com",
    "throwaway.email",
}


def check_email(
    email: str,
    settings: VerificationSettings | None = None,
    strict_mode: bool = False,
) -> tuple[str, str]:
    """
    Verify an email address through multiple checks.

    Returns:
        tuple: (status, reason) where status is 'valid', 'invalid', or 'risky'
    """
    settings = settings or VerificationSettings()

    if not EMAIL_REGEX.match(email):
        return "invalid", "bad_syntax"

    domain = email.split("@")[1]
    local = email.split("@")[0]

    if domain.lower() in DISPOSABLE_DOMAINS:
        return "invalid", "disposable_domain"

    role_based_prefixes = {"info", "support", "admin", "sales", "contact", "help", "noreply"}
    if local.lower() in role_based_prefixes and strict_mode:
        return "invalid", "role_based"

    try:
        records = dns.resolver.resolve(domain, "MX")
        mx_records = sorted([(r.preference, str(r.exchange)) for r in records])
        if not mx_records:
            return "invalid", "no_mx"
        mx_record = mx_records[0][1]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return "invalid", "no_mx"
    except Exception:
        return "risky", "dns_error"

    return smtp_verify_with_retry(email, mx_record, settings)


def smtp_verify_with_retry(
    email: str,
    mx_record: str,
    settings: VerificationSettings,
) -> tuple[str, str]:
    sender_domain = settings.sender_domain
    sender_email = settings.sender_email
    timeout = settings.timeout_seconds
    max_retries = max(1, settings.retry_count + 1)

    def single_smtp_check(retry_delay: int = 0) -> tuple[int | None, str]:
        if retry_delay > 0:
            time.sleep(retry_delay)

        try:
            server = smtplib.SMTP(timeout=timeout)
            server.connect(mx_record.rstrip("."), 25)
            server.helo(sender_domain)
            server.mail(sender_email)
            code, message = server.rcpt(email)
            server.quit()

            if isinstance(message, bytes):
                message = message.decode("utf-8", errors="ignore")

            return code, str(message)
        except smtplib.SMTPServerDisconnected:
            return None, "disconnected"
        except smtplib.SMTPConnectError:
            return None, "connection_failed"
        except socket.timeout:
            return None, "timeout"
        except Exception as exc:
            return None, str(exc)

    def parse_550_message(message: str) -> str:
        message_lower = message.lower()

        invalid_patterns = [
            "mailbox not found",
            "user not found",
            "user unknown",
            "no such user",
            "recipient not found",
            "mailbox unavailable",
            "does not exist",
            "invalid recipient",
            "address rejected",
            "unknown user",
            "no mailbox",
            "mailbox does not exist",
            "recipient rejected",
            "user does not exist",
            "addressee unknown",
        ]

        block_patterns = [
            "verification",
            "policy",
            "not permitted",
            "blocked",
            "spam",
            "administrative prohibition",
            "relay",
            "access denied",
            "prohibited",
            "authentication required",
        ]

        for pattern in invalid_patterns:
            if pattern in message_lower:
                return "invalid"

        for pattern in block_patterns:
            if pattern in message_lower:
                return "risky"

        return "risky"

    retry_delays = [0] + [3 * i for i in range(1, max_retries)]
    last_code = None
    last_message = None

    for attempt in range(max_retries):
        delay = retry_delays[attempt] if attempt < len(retry_delays) else 0
        code, message = single_smtp_check(delay)
        last_code = code
        last_message = message

        if code == 250:
            return "valid", "smtp_ok"

        if code == 550:
            status = parse_550_message(last_message or "")
            if status == "invalid":
                return "invalid", "smtp_550_mailbox_not_found"
            if attempt < max_retries - 1:
                continue
            return "risky", "smtp_550_verification_blocked"

        if code in [551, 552, 553]:
            return "invalid", f"smtp_{code}"

        if code in [421, 450, 451, 452]:
            if attempt < max_retries - 1:
                continue
            return "risky", f"greylist_code_{code}"

        if code in [422, 431, 432, 442, 447, 449, 503]:
            if attempt < max_retries - 1:
                continue
            return "risky", "rate_limited_or_temp_error"

        if code is None:
            if "timeout" in str(last_message):
                if attempt < max_retries - 1:
                    continue
                return "risky", "smtp_timeout"
            if "connection" in str(last_message):
                if attempt < max_retries - 1:
                    continue
                return "risky", "smtp_connection_failed"
            if attempt < max_retries - 1:
                continue
            return "risky", "smtp_verification_failed"

        if attempt < max_retries - 1:
            continue

    if last_code:
        return "risky", f"smtp_code_{last_code}"
    return "risky", "smtp_inconclusive"


def check_email_simple(email: str) -> tuple[str, str]:
    """Syntax and DNS only (no SMTP)."""
    if not EMAIL_REGEX.match(email):
        return "invalid", "bad_syntax"

    domain = email.split("@")[1]

    if domain.lower() in DISPOSABLE_DOMAINS:
        return "invalid", "disposable_domain"

    try:
        records = dns.resolver.resolve(domain, "MX")
        if records:
            return "valid", "dns_valid"
    except Exception:
        return "invalid", "no_mx"

    return "risky", "unknown"
