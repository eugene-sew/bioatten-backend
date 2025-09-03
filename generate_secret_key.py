#!/usr/bin/env python
"""
Generate a secure 256-bit secret key for Django
"""
import secrets
import string

def generate_secret_key(length=64):
    """Generate a secure random string of specified length."""
    # Use a combination of letters, digits, and special characters
    characters = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(secrets.choice(characters) for _ in range(length))

if __name__ == "__main__":
    # Generate a 256-bit (32 bytes) key, represented as 64 hex characters
    secret_key = generate_secret_key(64)
    print(f"Generated SECRET_KEY: {secret_key}")
    print("\nAdd this to your .env file:")
    print(f"SECRET_KEY={secret_key}")
