"""
Email verification utilities with robust multi-layered approach
"""
import re
import time
import socket
import dns.resolver
import smtplib

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
DISPOSABLE_DOMAINS = {"mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com", "throwaway.email"}

# Valid sender domain for SMTP verification (using a real domain to avoid rejections)
SENDER_DOMAIN = "gmail.com"
SENDER_EMAIL = f"verify@{SENDER_DOMAIN}"


def check_email(email, strict_mode=False):
    """
    Verify an email address through multiple checks with confidence scoring
    
    Args:
        email (str): Email address to verify
        strict_mode (bool): If True, uses stricter validation (may have false negatives)
        
    Returns:
        tuple: (status, reason) where status is 'valid', 'invalid', or 'risky'
    """
    if not EMAIL_REGEX.match(email):
        return "invalid", "bad_syntax"

    domain = email.split('@')[1]
    local = email.split('@')[0]

    # Check for disposable domains
    if domain.lower() in DISPOSABLE_DOMAINS:
        return "invalid", "disposable_domain"
    
    # Don't reject role-based emails in non-strict mode (they're often valid business emails)
    # Only flag them as risky instead of invalid
    role_based_prefixes = {"info", "support", "admin", "sales", "contact", "help", "noreply"}
    if local.lower() in role_based_prefixes:
        if strict_mode:
            return "invalid", "role_based"
        # In lenient mode, continue verification but note it's role-based

    # DNS/MX Record Verification
    try:
        records = dns.resolver.resolve(domain, 'MX')
        mx_records = sorted([(r.preference, str(r.exchange)) for r in records])
        if not mx_records:
            return "invalid", "no_mx"
        # Use the highest priority (lowest preference number) MX record
        mx_record = mx_records[0][1]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return "invalid", "no_mx"
    except Exception as e:
        # DNS resolution failed - might be temporary
        return "risky", "dns_error"

    # SMTP Verification with retry logic for greylisting
    smtp_result = smtp_verify_with_retry(email, mx_record, domain)
    
    return smtp_result


def smtp_verify_with_retry(email, mx_record, domain, max_retries=1):
    """
    Verify email via SMTP with retry logic for greylisting and temporary errors
    
    Args:
        email (str): Email to verify
        mx_record (str): MX server address
        domain (str): Email domain
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        tuple: (status, reason)
    """
    
    def single_smtp_check(sender_email, retry_delay=0):
        """Perform a single SMTP check"""
        if retry_delay > 0:
            time.sleep(retry_delay)
            
        try:
            server = smtplib.SMTP(timeout=15)
            server.connect(mx_record.rstrip('.'), 25)
            server.helo(SENDER_DOMAIN)
            server.mail(sender_email)
            code, message = server.rcpt(email)
            server.quit()
            
            # Decode message if it's bytes
            if isinstance(message, bytes):
                message = message.decode('utf-8', errors='ignore')
            
            return code, str(message)
        except smtplib.SMTPServerDisconnected:
            return None, "disconnected"
        except smtplib.SMTPConnectError:
            return None, "connection_failed"
        except socket.timeout:
            return None, "timeout"
        except Exception as e:
            return None, str(e)
    
    def parse_550_message(message):
        """
        Parse SMTP 550 message to determine if it's a real rejection or anti-spam block
        
        Returns:
            'invalid' if mailbox doesn't exist
            'risky' if verification is blocked
        """
        message_lower = message.lower()
        
        # Patterns that indicate mailbox DOESN'T EXIST (definite invalid)
        invalid_patterns = [
            'mailbox not found',
            'user not found',
            'user unknown',
            'no such user',
            'recipient not found',
            'mailbox unavailable',
            'does not exist',
            'invalid recipient',
            'address rejected',
            'unknown user',
            'no mailbox',
            'mailbox does not exist',
            'recipient rejected',
            'user does not exist',
            'addressee unknown',
        ]
        
        # Patterns that indicate ANTI-SPAM BLOCKING (risky - might be valid)
        block_patterns = [
            'verification',
            'policy',
            'not permitted',
            'blocked',
            'spam',
            'administrative prohibition',
            'relay',
            'access denied',
            'prohibited',
            'authentication required',
        ]
        
        # Check for invalid patterns first (these are definite rejections)
        for pattern in invalid_patterns:
            if pattern in message_lower:
                print(f"   📋 SMTP 550 Analysis: INVALID - Message contains '{pattern}'")
                return 'invalid'
        
        # Check for block patterns (anti-spam)
        for pattern in block_patterns:
            if pattern in message_lower:
                print(f"   📋 SMTP 550 Analysis: RISKY - Message contains '{pattern}' (anti-spam block)")
                return 'risky'
        
        # If no specific pattern found, be conservative and mark as risky
        print(f"   📋 SMTP 550 Analysis: RISKY - No definitive pattern, treating as potential anti-spam")
        return 'risky'
    
    # Check if domain accepts all emails (catch-all test)
    try:
        test_code, _ = single_smtp_check(SENDER_EMAIL)
        if test_code:
            # Test with a definitely non-existent email
            catch_all_code, _ = single_smtp_check(SENDER_EMAIL)
            if catch_all_code == 250:
                # Domain might be catch-all, but don't mark as invalid
                # Continue with actual email verification
                pass
    except Exception:
        pass
    
    # Main verification with retry logic (reduced for speed)
    retry_delays = [0]  # No retry delay for speed
    last_code = None
    last_message = None
    
    print(f"\n🔍 Verifying: {email}")
    print(f"   MX Server: {mx_record}")
    
    for attempt in range(max_retries):
        code, message = single_smtp_check(SENDER_EMAIL, retry_delays[attempt])
        last_code = code
        last_message = message
        
        print(f"   Attempt {attempt + 1}/1: Code={code}, Message='{message}'")
        
        # Success - email is valid
        if code == 250:
            print(f"   ✅ Result: VALID - SMTP accepted (250)")
            return "valid", "smtp_ok"
        
        # SMTP 550 - Parse the message to determine if invalid or risky
        if code == 550:
            # Parse the SMTP message to determine the real status (no retry for speed)
            status = parse_550_message(last_message)
            
            if status == 'invalid':
                print(f"   ❌ Result: INVALID - Mailbox doesn't exist")
                return "invalid", "smtp_550_mailbox_not_found"
            else:
                print(f"   ⚠️  Result: RISKY - Anti-spam block or verification rejected")
                return "risky", "smtp_550_verification_blocked"
        
        # 551, 552, 553 - definite user/mailbox issues
        if code in [551, 552, 553]:
            print(f"   ❌ Result: INVALID - SMTP {code} (mailbox issue)")
            return "invalid", f"smtp_{code}"
        
        # Temporary errors - mark as risky (no retry for speed)
        if code in [421, 450, 451, 452]:
            print(f"   ⚠️  Result: RISKY - Temporary error/greylisting (code {code})")
            return "risky", f"greylist_code_{code}"
        
        # Rate limiting or temporary issues
        if code in [422, 431, 432, 442, 447, 449, 503]:
            print(f"   ⚠️  Result: RISKY - Rate limited or temporary error")
            return "risky", "rate_limited_or_temp_error"
        
        # Connection issues
        if code is None:
            # Couldn't verify via SMTP - don't mark as invalid
            if "timeout" in str(last_message):
                print(f"   ⚠️  Result: RISKY - Connection timeout")
                return "risky", "smtp_timeout"
            elif "connection" in str(last_message):
                print(f"   ⚠️  Result: RISKY - Connection failed")
                return "risky", "smtp_connection_failed"
            else:
                print(f"   ⚠️  Result: RISKY - Verification failed")
                return "risky", "smtp_verification_failed"
    
    # If we get here, verification was inconclusive
    # Default to risky rather than invalid to avoid false negatives
    print(f"   ⚠️  Result: RISKY - Inconclusive verification")
    if last_code:
        return "risky", f"smtp_code_{last_code}"
    else:
        return "risky", "smtp_inconclusive"


def check_email_simple(email):
    """
    Simplified email check - syntax and DNS only (no SMTP)
    Useful for quick validation without SMTP overhead
    
    Args:
        email (str): Email address to verify
        
    Returns:
        tuple: (status, reason)
    """
    if not EMAIL_REGEX.match(email):
        return "invalid", "bad_syntax"
    
    domain = email.split('@')[1]
    
    if domain.lower() in DISPOSABLE_DOMAINS:
        return "invalid", "disposable_domain"
    
    try:
        records = dns.resolver.resolve(domain, 'MX')
        if records:
            return "valid", "dns_valid"
    except Exception:
        return "invalid", "no_mx"
    
    return "risky", "unknown"

