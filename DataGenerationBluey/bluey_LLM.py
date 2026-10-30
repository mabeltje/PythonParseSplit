"""
Calls the LLM API using settings imported from bluey.json.

query_llm(messages) takes a list of messages in the format:
"""

import json
import os
import requests
from dotenv import load_dotenv
from openai import OpenAI, APIError

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client pointed at UvA Proxy endpoint
client = OpenAI(
    base_url="https://llmproxy.uva.nl/v1",
    api_key=os.getenv("UVA_LLM_KEY")
)

def query_llm(messages: list[dict], model: str = "claude-sonnet-4.5") -> str | None:
    """
    Queries the LLM proxy with a list of messages and returns the text response.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2
        )
        return response.choices[0].message.content
        
    except APIError as e:
        print(f"LLM API Error ({e.status_code}): {e.message}")
        return None
    except Exception as e:
        print(f"Unexpected error querying LLM: {e}")
        return None
    