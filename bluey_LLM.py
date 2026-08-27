import json
import os
import requests

# Load config.json
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "bluey.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

def query_llm(messages):
    """
    Calls the LLM API using settings imported from bluey.json.
    """
    url = CONFIG["api_url"]
    headers = CONFIG.get("headers", {"Content-Type": "application/json"})
    
    # Merge base config data (like model) with the prompt messages
    payload = CONFIG.get("data", {}).copy()
    payload["messages"] = messages


    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"Error querying LLM: {e}")
        return None