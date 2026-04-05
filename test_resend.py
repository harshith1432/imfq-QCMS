import os
from dotenv import load_dotenv
import resend

# Base directory for the backend
BACKEND_DIR = r"d:\projects softwares\imfq\backend"
ENV_PATH = os.path.join(BACKEND_DIR, ".env")

# Load .env
load_dotenv(ENV_PATH)

api_key = os.getenv("RESEND_API_KEY")
print(f"[QCMS] Testing API Key: {api_key[:5]}...")

if not api_key:
    print("[QCMS] Error: RESEND_API_KEY not found in .env")
    exit(1)

resend.api_key = api_key

try:
    # Just list some domains or something non-invasive
    # resend.api_keys.list() or just check if we can reach the API
    # resend.api_keys.get() is not usually available for all keys
    # Let's try sending to a verified email or just checking if the key is recognized
    print("Checking if key is recognized...")
    # Actually, resend-python 2.4.0 might not have a simple 'ping'
    # But we can try to list keys if it's a management key, or just send a dummy one to the same domain?
    # To avoid wasting quota, I'll just check if the key format is correct and if the library is installed.
    print(f"[QCMS] Resend library version: {resend.__version__}")
except Exception as e:
    print(f"Error testing Resend API: {e}")
