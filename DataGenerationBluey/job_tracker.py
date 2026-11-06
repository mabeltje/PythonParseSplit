import json
import requests
from pathlib import Path

API_URL = "https://signcollect.nl/blendBaking/api.php"

def update_job(
    tracker_path: str | Path, 
    base_id: str, 
    status_update: str, 
    input_data: dict = None, 
    substitutions: list = None
) -> None:
    """Safely updates a specific job entry in job_tracker.json."""
    tracker_path = Path(tracker_path).resolve()
    tracker_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {}
    if tracker_path.is_file():
        with open(tracker_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}

    if base_id not in data:
        data[base_id] = {
            "status": "PENDING",
            "input": {
                "nederlands_zin": "",
                "original_glosses": [],
                "gvg_zin": []
            },
            "substitutions": []
        }

    job = data[base_id]

    if status_update:
        job["status"] = status_update

    if input_data:
        job["input"].update(input_data)

    if substitutions is not None:
        job["substitutions"] = substitutions

    with open(tracker_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def populate_job_tracker(filename: str | Path) -> Path:
    """Fetches available bases from the API and populates job_tracker.json without touching existing entries."""
    filepath = Path(filename).resolve()

    params = {"action": "bases"}
    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    api_data = response.json()

    if isinstance(api_data, dict) and not api_data.get("success", True):
        raise ValueError(f"API Error: {api_data.get('error', 'Unknown error')}")

    bases = api_data.get("bases", {})

    if not filepath.is_file() or filepath.stat().st_size == 0:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

    print(f"Populating job tracker with {len(bases)} base animations...")
    for base_id in bases:
        # Passing status_update={} ensures new base_ids get initialized 
        # with default PENDING state without overwriting existing data
        update_job(
            tracker_path=filepath,
            base_id=base_id,
            status_update={}
        )

    print(f"Successfully populated job tracker at '{filepath}'")
    return filepath