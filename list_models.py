#!/usr/bin/env python3
import os

from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    print("Available models:")
    for model in genai.list_models():
        if "generateContent" in model.supported_generation_methods:
            print(f"  - {model.name}")
except Exception as e:
    print(f"Error: {e}")
