"""
Email permutation generator
"""
import re
import dns.resolver
import requests
from urllib.parse import urlparse


def extract_domain_from_url(url):
    """
    Extract domain from URL
    
    Args:
        url (str): URL to extract domain from
        
    Returns:
        str: Domain name
    """
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    
    # Remove www. prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]
    
    return domain


def parse_name(name):
    """
    Parse full name into first and last name
    
    Args:
        name (str): Full name
        
    Returns:
        tuple: (first_name, last_name)
    """
    name = name.strip().lower()
    # Remove any special characters
    name = re.sub(r'[^a-z\s]', '', name)
    
    parts = name.split()
    
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    else:
        # First name is first part, last name is last part
        # (handles middle names by taking first and last)
        return parts[0], parts[-1]


def discover_subdomains_from_ct_logs(domain, timeout=5):
    """
    Discover subdomains using Certificate Transparency logs (crt.sh)
    
    Args:
        domain (str): Base domain to check
        timeout (int): Request timeout in seconds
        
    Returns:
        set: Set of discovered subdomains
    """
    subdomains = set()
    
    try:
        print(f"   🔐 Querying Certificate Transparency logs...")
        # Query crt.sh API
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == 200:
            certs = response.json()
            
            for cert in certs:
                name_value = cert.get('name_value', '')
                # Split by newlines (crt.sh returns multiple names per cert)
                names = name_value.split('\n')
                
                for name in names:
                    name = name.strip().lower()
                    # Skip wildcards and the base domain
                    if name and '*' not in name and name != domain:
                        # Only keep subdomains of our target domain
                        if name.endswith(f'.{domain}'):
                            subdomains.add(name)
            
            print(f"   ✅ Found {len(subdomains)} subdomains from CT logs")
        else:
            print(f"   ⚠️  CT logs query failed (HTTP {response.status_code})")
    
    except requests.Timeout:
        print(f"   ⚠️  CT logs query timed out")
    except Exception as e:
        print(f"   ⚠️  CT logs error: {str(e)}")
    
    return subdomains


def discover_email_subdomains(domain):
    """
    Discover subdomains with MX records using Certificate Transparency logs + fallback
    
    Args:
        domain (str): Base domain to check
        
    Returns:
        list: List of domains/subdomains with MX records
    """
    domains_to_check = [domain]
    
    print(f"\n🔍 Discovering email subdomains for: {domain}")
    
    # Step 1: Try Certificate Transparency logs first
    ct_subdomains = discover_subdomains_from_ct_logs(domain)
    
    # Step 2: Fallback to common patterns if CT fails
    if not ct_subdomains:
        print(f"   📋 Using common subdomain patterns as fallback...")
        ct_subdomains = [
            f'{s}.{domain}' for s in ['mail', 'smtp', 'send', 'rs', 'mx', 'email', 'webmail']
        ]
    
    # Step 3: Check which discovered subdomains have MX records
    print(f"   🔍 Checking {len(ct_subdomains)} subdomains for MX records...")
    
    for subdomain_fqdn in ct_subdomains:
        try:
            records = dns.resolver.resolve(subdomain_fqdn, 'MX')
            if records:
                mx_server = str(records[0].exchange)
                print(f"   ✅ Found: {subdomain_fqdn} → MX: {mx_server}")
                domains_to_check.append(subdomain_fqdn)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            # No MX record for this subdomain
            pass
        except Exception as e:
            # Ignore other errors
            pass
    
    print(f"   📧 Total domains with MX records: {len(domains_to_check)}")
    return domains_to_check


def generate_email_permutations(name, url):
    """
    Generate all possible email permutations for a given name and domain
    Including subdomain variations (e.g., user@rs.domain.com)
    
    Args:
        name (str): Full name (e.g., "Shubham Kashyap")
        url (str): Website URL (e.g., "https://fusionsync.ai")
        
    Returns:
        list: List of possible email addresses
    """
    base_domain = extract_domain_from_url(url)
    first, last = parse_name(name)
    
    if not base_domain:
        return []
    
    # Discover all domains/subdomains with MX records
    email_domains = discover_email_subdomains(base_domain)
    
    permutations = []
    
    # Generate permutations for EACH domain/subdomain
    for domain in email_domains:
        # If we have both first and last name
        if first and last:
            # Most common combinations (removed - and _ for speed)
            permutations.extend([
                f"{first}@{domain}",                    # first@domain
                f"{last}@{domain}",                     # last@domain
                f"{first}.{last}@{domain}",             # first.last@domain
                f"{last}.{first}@{domain}",             # last.first@domain
                f"{first}{last}@{domain}",              # firstlast@domain
                
                # With initials (most common)
                f"{first[0]}.{last}@{domain}",          # f.last@domain
                f"{first}.{last[0]}@{domain}",          # first.l@domain
                f"{first[0]}{last}@{domain}",           # flast@domain
            ])
        elif first:
            # Only first name available
            permutations.extend([
                f"{first}@{domain}",
            ])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_permutations = []
    for email in permutations:
        if email not in seen and email.count('@') == 1:
            seen.add(email)
            unique_permutations.append(email)
    
    print(f"   📨 Generated {len(unique_permutations)} unique email permutations")
    return unique_permutations

