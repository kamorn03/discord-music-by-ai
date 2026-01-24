#!/usr/bin/env python3
"""
Network diagnostic script for Railway deployment
Run this to check Lavalink connectivity before starting the bot
"""

import socket
import os
import sys
from urllib.parse import urlparse

def print_separator():
    print("=" * 70)

def check_dns(hostname):
    """Check DNS resolution"""
    print(f"\n[DNS] Resolving hostname: {hostname}")
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✓ SUCCESS: {hostname} -> {ip}")
        return ip
    except socket.gaierror as e:
        print(f"✗ FAILED: Cannot resolve {hostname}")
        print(f"  Error: {e}")
        return None
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return None

def check_port(hostname, port):
    """Check if port is reachable"""
    print(f"\n[TCP] Testing connection to {hostname}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            print(f"✓ SUCCESS: Port {port} is OPEN")
            return True
        else:
            print(f"✗ FAILED: Port {port} is CLOSED (error code: {result})")
            return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

def get_local_info():
    """Get local network information"""
    print(f"\n[LOCAL] Getting local network information")
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        print(f"✓ Local hostname: {hostname}")
        print(f"✓ Local IP: {ip}")
        return hostname, ip
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return None, None

def check_env_vars():
    """Check environment variables"""
    print(f"\n[ENV] Checking environment variables")
    
    required_vars = {
        'DISCORD_TOKEN': 'Discord bot token',
        'DISCORD_APP_ID': 'Discord application ID',
        'LAVALINK_URI': 'Lavalink server URI',
        'LAVALINK_PASSWORD': 'Lavalink password'
    }
    
    all_present = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            if 'TOKEN' in var or 'PASSWORD' in var or 'SECRET' in var:
                display_value = '*' * min(len(value), 20)
            else:
                display_value = value
            print(f"✓ {var} = {display_value}")
        else:
            print(f"✗ {var} is NOT SET ({description})")
            all_present = False
    
    return all_present

def main():
    print_separator()
    print("RAILWAY DEPLOYMENT - NETWORK DIAGNOSTICS")
    print_separator()
    
    # Check environment variables
    env_ok = check_env_vars()
    
    # Get Lavalink URI
    lavalink_uri = os.getenv('LAVALINK_URI', 'http://localhost:2333')
    print(f"\n[CONFIG] Lavalink URI: {lavalink_uri}")
    
    # Parse URI
    try:
        parsed = urlparse(lavalink_uri)
        hostname = parsed.hostname or 'localhost'
        port = parsed.port or 2333
        print(f"[CONFIG] Parsed hostname: {hostname}")
        print(f"[CONFIG] Parsed port: {port}")
    except Exception as e:
        print(f"✗ ERROR parsing URI: {e}")
        sys.exit(1)
    
    print_separator()
    
    # Get local network info
    get_local_info()
    
    # Check DNS
    ip = check_dns(hostname)
    
    # Check port connectivity
    if ip:
        check_port(hostname, port)
    
    print_separator()
    print("\n[SUMMARY]")
    
    if not env_ok:
        print("⚠ WARNING: Some environment variables are missing")
    
    if ip:
        print(f"✓ DNS resolution successful: {hostname} -> {ip}")
    else:
        print(f"✗ DNS resolution failed for: {hostname}")
        print("\n[TIPS FOR RAILWAY]")
        print("  1. Make sure Lavalink service is deployed")
        print("  2. Use internal hostname: http://lavalink.railway.internal:2333")
        print("  3. Enable Private Networking in both services")
        print("  4. Wait 30-60 seconds after deployment for DNS propagation")
    
    print_separator()
    print("\n[RAILWAY INTERNAL HOSTNAMES]")
    print("  Format: <service-name>.railway.internal")
    print("  Example: lavalink.railway.internal")
    print("  Port: 2333 (default Lavalink port)")
    print("\n  Correct URI: http://lavalink.railway.internal:2333")
    print("  Wrong URI: http://127.0.0.1:2333 (localhost doesn't work on Railway)")
    print_separator()

if __name__ == "__main__":
    main()
