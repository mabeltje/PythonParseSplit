import json
import os
from bluey_LLM import query_llm

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_sentence_substitutions(glosses_file, sentences_file, rules_file, output_file):
    available_glosses = load_json(glosses_file)
    sentences_data = load_json(sentences_file)
    system_prompt = load_json(rules_file)  # Load system rules from file

    user_prompt = f"""
    AVAILABLE GLOSSES FOR SUBSTITUTION:
    {json.dumps(available_glosses)}

    INPUT SENTENCES:
    {json.dumps(sentences_data)}

    SYSTEM RULES:
    {json.dumps(system_prompt)}

    Generate variation instances as a JSON array following the requested structure for all input sentences.
    """

    messages = [
        {"role": "system", "content": json.dumps(system_prompt)},
        {"role": "user", "content": user_prompt}
    ]

    print("Requesting substitution variations from LLM...")
    raw_response = query_llm(messages)

    if not raw_response:
        print("Failed to get response from LLM.")
        return

    try:
        clean_response = raw_response.strip()
        if clean_response.startswith("```"):
            clean_response = clean_response.split("```")[1]
            if clean_response.startswith("json"):
                clean_response = clean_response[4:]
        
        parsed_data = json.loads(clean_response.strip())
        save_json(parsed_data, output_file)
        print(f"Successfully generated substitutions and saved to '{output_file}'!")

    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response as valid JSON: {e}")
        print("Raw output was:\n", raw_response)

if __name__ == "__main__":
    generate_sentence_substitutions(
        glosses_file="all_glosses.json",
        sentences_file="all_sentences.json",
        rules_file="rules.json",
        output_file="substitutions_output.json"
    )