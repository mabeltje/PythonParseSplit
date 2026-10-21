"""
This script fetches glosses and sentences from the BlendBaking API and saves them to JSON files.

fetch_and_save_glosses(filename): Fetches all glosses with their senses from the API and saves them to the specified JSON file.
fetch_and_save_sentences(filename, page=1, limit=200): Fetches sentences from the API, transforms them into the desired JSON structure, 
and saves them to the specified JSON file. 

"""

import json
import requests
from pathlib import Path
import sys

# Add project root (PythonParseSplit) to Python search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from DataFetch.call_api import get_senses

API_URL = "https://signcollect.nl/blendBaking/api.php"
MODULE_DIR = Path(__file__).resolve().parent

def fetch_gloss_variants_mapping(filename: str | Path) -> Path:
    filepath = Path(filename).resolve()
    filepath.parent.mkdir(parents=True, exist_ok=True)

    params = {"action": "glosses", "mcpStatusTijdAnnotatie": "Klaar"}

    # Make the GET request
    response = requests.get(API_URL, params=params)
    response.raise_for_status()  # Check for network/HTTP errors

    data = response.json()

    # The API returns HTTP 200 even on error, so check the "success" key
    if isinstance(data, dict) and not data.get("success", True):
        raise ValueError(f"API Error: {data.get('error', 'Unknown error')}")
    
    bases = data.get("bases", {})
    base_variants_map = {base_name: list(base_info.get("variants", []).keys()) for base_name, base_info in bases.items()}

    # Save the base variants mapping to a JSON file into a subdirectory of the project root
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(base_variants_map, f, ensure_ascii=False, indent=4)

    return filepath

def fetch_and_save_glosses(filename: str | Path) -> Path:
    filepath = Path(filename).resolve()
    filepath.parent.mkdir(parents=True, exist_ok=True)

    params = {"action": "glosses", "mcpStatusTijdAnnotatie": "Klaar"}

    # Make the GET request
    response = requests.get(API_URL, params=params)
    response.raise_for_status()  # Check for network/HTTP errors

    data = response.json()

    # The API returns HTTP 200 even on error, so check the "success" key
    if isinstance(data, dict) and not data.get("success", True):
        raise ValueError(f"API Error: {data.get('error', 'Unknown error')}")

    bases = data.get("bases", {})
    bases_variants = []

    for base_name, base_info in bases.items():
        bases_variants.extend(base_info.get("variants", []))

    variants_with_senses = {}

    for base in bases_variants:
            # Fetch senses for each gloss (where base is a string variant name)
            senses = get_senses(base)
            variants_with_senses[base] = senses

    # Save to JSON file with clean formatting and UTF-8 encoding
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(variants_with_senses, f, ensure_ascii=False, indent=4)

    print(f"Successfully saved glosses to '{filepath}'")
    return filepath


def fetch_and_save_sentences(filename: str | Path, page: int = 1, limit: int = 200) -> Path:
    filepath = Path(filename).resolve()
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Only the first page for now, as the API returns a maximum of 200 sentences per page
    # Need to find a way to fetch all pages eventually
    params = {
        "action": "timings",
        "page": page,
        "limit": limit,
        "mcpStatusTijdAnnotatie": "Klaar"
    }

    response = requests.get(API_URL, params=params)
    response.raise_for_status()

    data = response.json()
    if isinstance(data, dict) and not data.get("success", True):
        raise ValueError(f"API Error: {data.get('error', 'Unknown error')}")

    output_data = []
    sentences = data.get("sentences", [])

    for sentence in sentences:
        formatted_item = {
            "original_animation": sentence.get("base", ""),
            "glosses": [g.get("gloss") for g in sentence.get("glosses", [])],
            "zin": sentence.get("zin", ""),
            "substitutions": []
        }
        output_data.append(formatted_item)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    print(f"Successfully saved sentences to '{filepath}'")
    return filepath

def run_fetch(glosses_output: str | Path, sentences_output: str | Path, glosses_variants_output: str | Path, page: int = 1, limit: int = 200):
    """Unified entry function to call directly from pipeline_runner.py"""
    glosses_path = fetch_and_save_glosses(glosses_output)
    glosses_variants_path = fetch_gloss_variants_mapping(glosses_variants_output)
    sentences_path = fetch_and_save_sentences(sentences_output, page=page, limit=limit)
    return glosses_path, glosses_variants_path, sentences_path


if __name__ == "__main__":
    # Direct execution fallback writes to jobs/intermediate relative to project root
    project_root = MODULE_DIR.parent
    target_dir = project_root / "jobs" / "intermediate"

    run_fetch(
        glosses_output=target_dir / "all_glosses.json",
        glosses_variants_output=target_dir / "base_variants_map.json",
        sentences_output=target_dir / "all_sentences.json",
        page=3,
        limit=2
    )