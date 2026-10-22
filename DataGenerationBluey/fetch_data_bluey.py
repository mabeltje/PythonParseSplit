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
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    print(f"Successfully saved base variants mapping to '{filepath}'")

    return filepath

def fetch_and_save_glosses(filename: str | Path, max_workers: int = 10) -> Path:
    filepath = Path(filename).resolve()
    filepath.parent.mkdir(parents=True, exist_ok=True)

    params = {"action": "glosses", "mcpStatusTijdAnnotatie": "Klaar"}
    response = requests.get(API_URL, params=params)
    response.raise_for_status()

    data = response.json()
    if isinstance(data, dict) and not data.get("success", True):
        raise ValueError(f"API Error: {data.get('error', 'Unknown error')}")

    bases = data.get("bases", {})
    
    # Extract unique variant names
    unique_variants = set()
    for base_info in bases.values():
        variants = base_info.get("variants", {})
        if isinstance(variants, dict):
            for v in variants.keys():
                clean_v = str(v).strip()
                if clean_v and clean_v.lower() != "nvt":
                    unique_variants.add(clean_v)

    variants_with_senses = {}

    def _fetch_sense(variant):
        try:
            return variant, get_senses(variant)
        except Exception as e:
            print(f"Warning: Failed to fetch senses for {variant}: {e}")
            return variant, []

    # Fetch senses in parallel across threads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_fetch_sense, v) for v in unique_variants]
        for future in as_completed(futures):
            variant, senses = future.result()
            variants_with_senses[variant] = senses

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
        nederlandse_zin = sentence.get("nederlandsSrt", "")
        if not nederlandse_zin:
            print(f"Warning: Sentence ID {sentence.get('id')} has no 'nederlandsSrt'. Skipping.")
            continue

        # open the link nederlandse zin
        response = requests.get(nederlandse_zin)
        if response.status_code != 200:
            print(f"Warning: Failed to fetch SRT for sentence ID {sentence.get('id')}. Skipping.")
            continue

        srt_content = response.text
        lines = srt_content.splitlines()
        clean_lines = []

        for line in lines:
            line = line.strip()
            # Sla lege regels, getallen (regelnummers) en tijdstempels (bevat ->) over
            if not line or line.isdigit() or "-->" in line:
                continue
            clean_lines.append(line)

        nederlandse_zin_cleaned = " ".join(clean_lines)
        # TODO: add this to other function

        gvg_response = requests.get(sentence.get("gvgSrt", ""))
        if gvg_response.status_code != 200:
            print(f"Warning: Failed to fetch GVG SRT for sentence ID {sentence.get('id')}. Skipping.")
            continue

        gvg_srt_content = gvg_response.text
        gvg_lines = gvg_srt_content.splitlines()

        gvg_clean_lines = []
        for line in gvg_lines:
            line = line.strip()
            # Sla lege regels, getallen (regelnummers) en tijdstempels (bevat ->) over
            if not line or line.isdigit() or "-->" in line:
                continue
            gvg_clean_lines.append(line)

        gvg_zin_cleaned = " ".join(gvg_clean_lines)
        # TODO: how to match this with glosses? 

        formatted_item = {
            "original_animation": sentence.get("base", ""),
            "original_glosses": [g.get("gloss") for g in sentence.get("glosses", [])],
            "original_zin": sentence.get("zin", ""),
            # "nederlands_zin": nederlandse_zin_cleaned,
            "gvg_zin": gvg_zin_cleaned,
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