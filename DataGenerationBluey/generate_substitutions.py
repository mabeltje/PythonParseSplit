import json
import os
from DataGenerationBluey.bluey_LLM import query_llm
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent

def load_json(filepath: Path) -> dict | list:
    if not filepath.is_file():
        raise FileNotFoundError(f"Input file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data: dict | list, filepath: Path) -> None:
    # Ensure intermediate/output directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_sentence_substitutions(
    glosses_file: str | Path,
    sentences_file: str | Path,
    output_file: str | Path,
    rules_file: str | Path = None
) -> Path:

    glosses_path = Path(glosses_file).resolve()
    sentences_path = Path(sentences_file).resolve()
    out_path = Path(output_file).resolve()
    rules_path = Path(rules_file).resolve() if rules_file else (MODULE_DIR / "rules.json")

    available_glosses = load_json(glosses_path)
    sentences_data = load_json(sentences_path)
    system_prompt = load_json(rules_path)  # Load system rules from file

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
        raise RuntimeError("Failed to get response from LLM.")

    clean_response = raw_response.strip()
    if clean_response.startswith("```"):
        clean_response = clean_response.split("```")[1]
        if clean_response.startswith("json"):
            clean_response = clean_response[4:]
    
    parsed_data = json.loads(clean_response.strip())

    save_json(parsed_data, out_path)
    print(f"Successfully generated substitutions and saved to '{out_path}'!")


def run_generate(glosses_file: str | Path, sentences_file: str | Path, output_file: str | Path, rules_file: str | Path = None):
    """Unified entry function to call directly from pipeline_runner.py"""
    return generate_sentence_substitutions(glosses_file, sentences_file, output_file, rules_file)

if __name__ == "__main__":
    PROJECT_ROOT = MODULE_DIR.parent
    DEFAULT_INTERMEDIATE = PROJECT_ROOT / "jobs" / "intermediate"
    DEFAULT_UNREAL_READY = PROJECT_ROOT / "jobs" / "unreal_ready"

    run_generate(
        glosses_file=DEFAULT_INTERMEDIATE / "all_glosses.json",
        sentences_file=DEFAULT_INTERMEDIATE / "all_sentences.json",
        output_file=DEFAULT_UNREAL_READY / "substitutions_output.json",
        rules_file=MODULE_DIR / "rules.json"
    )