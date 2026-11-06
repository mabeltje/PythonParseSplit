import json
import os
from pathlib import Path
from DataGenerationBluey.bluey_LLM import query_llm
from DataGenerationBluey.job_tracker import update_job

MODULE_DIR = Path(__file__).resolve().parent

def load_json(filepath: Path) -> dict | list:
    if not filepath.is_file():
        raise FileNotFoundError(f"Input file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def load_text(filepath: Path) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()

def save_json(data: dict | list, filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_sentence_substitutions(
    glosses_file: str | Path,
    output_file: str | Path,
    job_tracker_file: str | Path,
    limit: int,
) -> Path:

    glosses_path = Path(glosses_file).resolve()
    out_path = Path(output_file).resolve()
    
    # Default to system_prompt.md
    rules_path = (MODULE_DIR / "system_prompt.md")
    job_tracker_path = Path(job_tracker_file).resolve()
    job_tracker = load_json(job_tracker_path)
    
    available_glosses = load_json(glosses_path)

    # Get the first 'limit' number of sentences that are marked as "LLM_READY" in the job tracker
    sentences_data = []
    for base_id, job in job_tracker.items():
        if job.get("status", {}) == "LLM_READY":
            sentences_data.append({
                "original_animation": base_id,
                "nederlands_zin": job.get("input", {}).get("nederlands_zin", ""),
                "original_glosses": job.get("input", {}).get("original_glosses", []),
                "gvg_zin": job.get("input", {}).get("gvg_zin", []),
                "substitutions": []
            })
        if len(sentences_data) >= limit:
            break
    
    # Load system prompt directly as raw text / markdown
    system_prompt = load_text(rules_path)

    # Read template and fill in variables
    user_template = load_text(MODULE_DIR / "user_prompt.md")

    user_prompt = user_template.format(
        available_glosses=json.dumps(available_glosses, ensure_ascii=False, indent=2),
        sentences_data=json.dumps(sentences_data, ensure_ascii=False, indent=2)
    )

    messages = [
        {"role": "system", "content": system_prompt},
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

    # Update the job tracker with the substitutions for each base_id
    for item in parsed_data:
        base_id = item.get("original_animation")
        substitutions = item.get("substitutions", [])
        update_job(job_tracker_path, base_id, status_update="LLM_DONE", substitutions=substitutions)

    # save_json(parsed_data, out_path)
    # print(f"Successfully generated substitutions and saved to '{out_path}'")
    return out_path

if __name__ == "__main__":
    PROJECT_ROOT = MODULE_DIR.parent
    DEFAULT_INTERMEDIATE = PROJECT_ROOT / "jobs" / "intermediate"
    DEFAULT_UNREAL_READY = PROJECT_ROOT / "jobs" / "unreal_ready"

    generate_sentence_substitutions(
        glosses_file=DEFAULT_INTERMEDIATE / "all_glosses.json",
        job_tracker_file=DEFAULT_INTERMEDIATE / "job_tracker.json",
        output_file=DEFAULT_UNREAL_READY / "substitutions_output.json",
        rules_file=MODULE_DIR / "system_prompt.md"
    )