import os
from dotenv import load_dotenv
from openai import OpenAI

# Load variables from .env file into environment
load_dotenv()

# Retrieve API key from environment
api_key = os.getenv("UVA_LLM_KEY")

if not api_key:
    raise ValueError("UVA_LLM_KEY is not set in the .env file")

client = OpenAI(
    base_url="https://llmproxy.uva.nl/v1",
    api_key=api_key
)

response = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain what you know about the grammar of Dutch Sign Language (NGT) in a concise manner."}
    ]
)

print(response.choices[0].message.content)