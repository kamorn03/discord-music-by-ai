#!/usr/bin/env python3
"""
Script to get YouTube OAuth2 refresh token for Lavalink
Run this on your LOCAL machine (not server) because it opens a browser

Usage:
1. Install: pip install google-auth-oauthlib
2. Run: python get_youtube_token.py
3. Follow the prompts
"""

import json

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Please install google-auth-oauthlib first:")
    print("  pip install google-auth-oauthlib")
    exit(1)

# YouTube scopes needed
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

def main():
    print("=" * 60)
    print("YouTube OAuth2 Token Generator for Lavalink")
    print("=" * 60)
    print()
    
    # Get client credentials from user
    print("Enter your OAuth2 credentials from Google Cloud Console:")
    print()
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required!")
        return
    
    # Create client config
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    print()
    print("Opening browser for authorization...")
    print("Please login with your Google account and allow access.")
    print()
    
    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        credentials = flow.run_local_server(port=0)
        
        print()
        print("=" * 60)
        print("SUCCESS! Here is your refresh token:")
        print("=" * 60)
        print()
        print(f"Refresh Token: {credentials.refresh_token}")
        print()
        print("=" * 60)
        print("Add this to your application.yml:")
        print("=" * 60)
        print()
        print("plugins:")
        print("  youtube:")
        print("    enabled: true")
        print("    oauth:")
        print("      enabled: true")
        print(f'      refreshToken: "{credentials.refresh_token}"')
        print()
        print("=" * 60)
        print("Done! Copy the refreshToken above to your application.yml")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
        print()
        print("If browser didn't open, try running this on a machine with a browser.")

if __name__ == "__main__":
    main()
