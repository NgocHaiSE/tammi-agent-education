"""
Check environment variables
"""
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

print("="*80)
print("Environment Variables Check")
print("="*80)

vars_to_check = [
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL", 
    "LLM_PROVIDER",
    "LLM_MODEL",
    "OPENAI_API_KEY",
]

for var in vars_to_check:
    value = os.environ.get(var, "NOT SET")
    print(f"{var:25} = {value}")

print("\n" + "="*80)
print("Testing settings module")
print("="*80)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.config.settings import get_settings

settings = get_settings()
print(f"OLLAMA_BASE_URL from settings = {settings.OLLAMA_BASE_URL}")
print(f"OLLAMA_MODEL from settings    = {settings.OLLAMA_MODEL}")
print(f"LLM_PROVIDER from settings    = {settings.LLM_PROVIDER}")
print(f"LLM_MODEL from settings        = {settings.llm_model}")

print("\n" + "="*80)
