"""
scerp/load_env_windows.py

needed for loading .env in windows
"""
import os
from dotenv import load_dotenv

# Load env
load_dotenv()
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")
