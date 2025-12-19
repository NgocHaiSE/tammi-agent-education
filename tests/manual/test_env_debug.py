from dotenv import load_dotenv
import os

load_dotenv('../.env')

v1 = os.getenv('OPENAI_BASE_URL')
v2 = os.getenv('NOTEXIST')

print(f'OPENAI_BASE_URL: {repr(v1)}')
print(f'NOTEXIST: {repr(v2)}')
print(f'Empty string is falsy: {bool("")}')
print(f'None is falsy: {bool(None)}')
print(f'Chain with empty: {repr(None or "" or "default")}')
print(f'Chain with None: {repr(None or None or "default")}')

# Simulate the exact logic from llm_service.py
endpoint = (None or 
           os.getenv("OPENAI_BASE_URL") or 
           None or 
           None)

print(f'\nEndpoint from chain (like llm_service.py): {repr(endpoint)}')
print(f'if endpoint check: {bool(endpoint)}')
