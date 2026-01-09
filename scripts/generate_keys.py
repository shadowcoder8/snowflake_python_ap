"""
------------------------------------------------------------------------------
Project: Snowflake Data Product API
Developer: Rikesh Chhetri
Description: Utility script to generate secure, random API keys.
------------------------------------------------------------------------------
"""
import sys
import os

# Add project root to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import generate_secure_key

if __name__ == "__main__":
    print("--- Secure API Key Generator ---")
    key = generate_secure_key()
    print(f"\nGenerated Key: {key}")
    print(f"\nAdd this to your .env file:")
    print(f"API_KEY={key}")
    print("\nFor multiple keys (key rotation), separate them with a comma:")
    print("API_KEY=<primary-key>,<secondary-key>")
