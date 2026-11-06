"""
This script fetches glosses and sentences from the BlendBaking API and saves them to JSON files.

fetch_and_save_glosses(filename): Fetches all glosses with their senses from the API and saves them to the specified JSON file.
fetch_and_save_sentences(filename, page=1, limit=200): Fetches sentences from the API, transforms them into the desired JSON structure, 
and saves them to the specified JSON file. 

"""

import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from DataFetch.call_api import get_senses
from DataGenerationBluey.job_tracker import update_job

API_URL = "https://signcollect.nl/blendBaking/api.php"

def fetch_gloss_variants_mapping(output_filename: str | Path) -> Path:
    """
    Fetches the mapping of base glosses to their variants and saves it to a JSON file.
    This is used later in the pipeline to get senses for each variant.
    """
    output_filepath = Path(output_filename).resolve()
    output_filepath.parent.mkdir(parents=True, exist_ok=True)

    api_params = {"action": "glosses"}

    # TODO: move all API calls to a separate function in call_api.py and add error handling
    response = requests.get(API_URL, params=api_params)
    response.raise_for_status()
    data = response.json()

    # The API returns HTTP 200 even on error, so check the "success" key
    if isinstance(data, dict) and not data.get("success", True):
        raise ValueError(f"API Error: {data.get('error', 'Unknown error')}")
    
    bases = data.get("bases", {})
    base_variants_map = {base_name: list(base_info.get("variants", []).keys()) for base_name, base_info in bases.items()}

    # Save the base variants mapping to a JSON file into a subdirectory of the project root
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(base_variants_map, f, ensure_ascii=False, indent=4)

    print(f"Successfully saved base variants mapping to '{output_filepath}'")

    return output_filepath


def fetch_glosses(output_filename: str | Path, max_workers: int = 15) -> Path:
    """
    Fetches all glosses with their senses and categories from the BlendBaking API and saves them to a JSON file.
    This function uses a ThreadPoolExecutor to fetch senses for each variant concurrently.
    """
    output_filepath = Path(output_filename).resolve()
    output_filepath.parent.mkdir(parents=True, exist_ok=True)

    # Fetch base glosses
    params = {"action": "glosses"}
    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and not data.get("success", True):
        raise ValueError(f"API Error: {data.get('error', 'Unknown error')}")

    # Extract base glosses and category lookup table
    bases = data.get("bases", {})
    category_map = data.get("categoryMap", {}).get("glosses", {})

    # Build unique variant -> category mapping
    variant_category_map = {}
    for base_name, base_info in bases.items():
        category = category_map.get(base_name, "Unknown")
        variants = base_info.get("variants", {})

        if isinstance(variants, dict):
            for variant in variants.keys():
                clean_variant = str(variant).strip()
                if clean_variant and clean_variant.lower() != "nvt":
                    variant_category_map[clean_variant] = category

    # Fetch senses concurrently
    def _fetch_sense(variant: str) -> tuple[str, list]:
        try:
            return variant, get_senses(variant)
        except Exception as e:
            print(f"Warning: Failed to fetch senses for '{variant}': {e}")
            return variant, []

    senses_map = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_fetch_sense, v) for v in variant_category_map.keys()]
        for future in as_completed(futures):
            variant, senses = future.result()
            senses_map[variant] = senses

    # Construct output dictionary
    final_gloss_structure = {
        variant: {
            "senses": senses,
            "category": variant_category_map.get(variant, "Unknown")
        }
        for variant, senses in senses_map.items()
    }

    # Save to file
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(final_gloss_structure, f, ensure_ascii=False, indent=4)

    print(f"Successfully saved glosses to '{output_filepath}'")
    return output_filepath


def _fetch_and_clean_srt(srt_url: str) -> list[str] | None:
    """
    Helper function to download an SRT file from a URL, filter out line numbers 
    and timestamps, and return a clean list of text lines.
    """
    if not srt_url:
        return None

    try:
        response = requests.get(srt_url)
        if response.status_code != 200:
            return None

        clean_lines = []
        for line in response.text.splitlines():
            line = line.strip()
            # Skip empty lines, sequence numbers, and timestamp arrows
            if not line or line.isdigit() or "-->" in line:
                continue
            clean_lines.append(line)

        return clean_lines
    except Exception as e:
        print(f"Warning: Failed to fetch/parse SRT from '{srt_url}': {e}")
        return None
    

def fetch_batch_sentences(job_tracker_output: str | Path, limit: int) -> Path:
    """
    Fetches a batch of sentences of size `limit` from the BlendBaking API that are marked as "PENDING" in the job tracker.
    It updates the job tracker to mark these sentences as "LLM_READY" and saves the relevant data.
    """
    job_tracker_path = Path(job_tracker_output).resolve()
    
    with open(job_tracker_path, "r", encoding="utf-8") as f:
        job_tracker_data = json.load(f)

    pending_ids = [
        base_id
        for base_id, job in job_tracker_data.items()
        if job.get("status", {}) == "PENDING"
    ]

    sentence_count = 0
    for base_id in pending_ids:
        params = {
            "action": "timings",
            "base": base_id,
        }

        response = requests.get(API_URL, params=params)
        response.raise_for_status()

        data = response.json()
        if isinstance(data, dict) and not data.get("success", True):
            raise ValueError(f"API Error: {data.get('error', 'Unknown error')}")
        
        sentences = data.get("sentences", [])
        if not sentences:
            continue
            
        sentence = sentences[0]
        if sentence.get("statusTijdAnnotatie") != "Klaar" or sentence.get("statusTijdAnnotatieGvg") != "Klaar":
            continue

        # Fetch and clean Dutch SRT content
        dutch_lines = _fetch_and_clean_srt(sentence.get("nederlandsSrt", ""))
        if not dutch_lines:
            print(f"Warning: Failed to process Nederlands SRT for sentence ID {sentence.get('id')}. Skipping.")
            continue
        nederlandse_zin_cleaned = " ".join(dutch_lines)

        # Fetch and clean GVG SRT content
        gvg_clean_lines = _fetch_and_clean_srt(sentence.get("gvgSrt", ""))
        if not gvg_clean_lines:
            print(f"Warning: Failed to process GVG SRT for sentence ID {sentence.get('id')}. Skipping.")
            continue

        original_glosses = [g.get("gloss") for g in sentence.get("glosses", [])]

        # Update the job tracker to mark this base_id as LLM_READY
        # Note: kwarg updated to status_updates (plural) to match job_tracker signature
        update_job(
            tracker_path=job_tracker_path, 
            base_id=base_id, 
            status_update="LLM_READY", 
            input_data={
                "nederlands_zin": nederlandse_zin_cleaned, 
                "original_glosses": original_glosses, 
                "gvg_zin": gvg_clean_lines
            }
        )

        sentence_count += 1
        if sentence_count >= limit:
            break

    return job_tracker_path

def run_fetch_setup(glosses_output: str | Path,  glosses_variants_output: str | Path):
    """Unified entry function to call directly from pipeline_runner.py"""
    glosses_variants_path = fetch_gloss_variants_mapping(glosses_variants_output)
    glosses_path = fetch_glosses(glosses_output)
    return glosses_path, glosses_variants_path


def run_fetch_sentences(job_tracker_output: str | Path, limit: int):
    """Fetches a batch of sentences and updates the job tracker."""
    sentences_path = fetch_batch_sentences(job_tracker_output, limit=limit)
    return sentences_path
