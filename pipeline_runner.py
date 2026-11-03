import json
import os
import argparse
import subprocess
from datetime import datetime, timezone
import requests
from pathlib import Path

# Import modular steps
from DataGenerationBluey.fetch_data_bluey import run_fetch
from DataGenerationBluey.generate_substitutions import generate_sentence_substitutions
from DataFetch.parse_split import run_parse_split

UE_CMD_PATH = "C:/Program Files/Epic Games/UE_5.7/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
UPROJECT_PATH = "C:/Users/visualisationLab/Documents/Unreal Projects/BlendingAutomation/BlendingAutomation.uproject"
API_URL = "https://signcollect.nl/blendBaking/api.php"

def run_unreal_headless(unreal_jobs_dir: str, unreal_output_dir: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ue_script_path = os.path.join(base_dir, "ue_process_jobs.py")

    if not os.path.exists(UE_CMD_PATH):
        raise FileNotFoundError(f"UnrealEditor-Cmd not found at {UE_CMD_PATH}")
    if not os.path.exists(UPROJECT_PATH):
        raise FileNotFoundError(f".uproject not found at {UPROJECT_PATH}")
    if not os.path.exists(ue_script_path):
        raise FileNotFoundError(f"Unreal script not found at {ue_script_path}")

    print(f"\nThe jobs directory for Unreal processing is: {unreal_jobs_dir}")
    cmd = [
        UE_CMD_PATH,
        UPROJECT_PATH,
        f"-ExecutePythonScript={ue_script_path}",
        "-nullrhi",          # Headless: disable rendering backend
        "-nosound",          # Headless: disable audio
        "-nopause",          # Headless: don't hang on warnings
        "-unattended",       # Headless: suppress popups and dialogs
        "-stdout",           # Forward logs to stdout
        # "-nosplash",         # Headless: disable splash screen
        # "-Interchange.FeatureFlags.Import.FBX=False", # Disable FBX EXPERIMENTAL import feature flag
        "-FullStdOutLogOutput",
        f"-jobs_dir={unreal_jobs_dir}"  # Custom argument passed to the UE script
        # "-nop4"
    ]

    # Pass the jobs directory via environment variables
    env = os.environ.copy()
    env["UE_JOBS_DIR"] = os.path.abspath(unreal_jobs_dir)
    env["UE_OUTPUT_DIR"] = os.path.abspath(unreal_output_dir)

    print(f"\n[Unreal] Launching headless Unreal Engine instance...")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        env=env
    )
    
    # Filter lines live as they are emitted
    keywords = (
    "[Headless Pipeline]",
    "[BlendingAutomation C++]",
    "LogTemp:",
    "LogPython: Error:",
    "LogPython: Warning:",
    "LogBlendingAuto"
    )    

    if process.stdout:
        for line in process.stdout:
            if any(k in line for k in keywords):
                print(line.rstrip())

    process.wait()

    if process.returncode != 0:
        print(f"\n[Unreal Error] Unreal exited with code {process.returncode}")
    else:
        print("\n[Unreal] Unreal process finished successfully!")

def populate_job_tracker(filename: str | Path) -> Path:
    """
    Fetches available bases from the API and initializes any new entries 
    in job_tracker.json without overwriting existing job states.
    """
    filepath = Path(filename).resolve()

    # 1. Fetch current bases from the API
    params = {"action": "bases"}
    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    api_data = response.json()

    if isinstance(api_data, dict) and not api_data.get("success", True):
        raise ValueError(f"API Error: {api_data.get('error', 'Unknown error')}")

    bases = api_data.get("bases", {})

    # 2. If file is completely empty, initialize it with an empty dict
    if not filepath.is_file() or filepath.stat().st_size == 0:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

    # 3. Check if file is valid JSON
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: '{filepath}' is not valid JSON.")
        return filepath


    # 4. Register/update each base using update_job
    print(f"Populating job tracker with {len(bases)} base animations...")
    for base_id in bases:
        # Update the job status for each base
        update_job(
            tracker_path=filepath,
            base_id=base_id,
            status_updates={}  # Preserves existing status if job already exists
        )

    print(f"Successfully populated job tracker at '{filepath}'")
    return filepath

def update_job(
    tracker_path: Path, 
    base_id: str, 
    status_updates: dict = None, 
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

    # Initialize job entry if missing
    if base_id not in data:
        data[base_id] = {
            "status": {
                "stage": "PENDING",
                "updated_at": None
            },
            "input": {
                "nederlands_zin": "",
                "original_glosses": [],
                "gvg_zin": []
            },
            "substitutions": []
        }

    job = data[base_id]

    if status_updates:
        job["status"].update(status_updates)
        job["status"]["updated_at"] = datetime.now(timezone.utc).isoformat()

    if input_data:
        job["input"].update(input_data)

    if substitutions is not None:
        job["substitutions"] = substitutions

    with open(tracker_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def run_pipeline(fetch_data: bool = True, generate_substitutions: bool = True, run_ue: bool = True, split_fbx: bool = True):
    """
    Runs the data fetching and saving pipeline to get all the data ready for Unreal.
    Parameters:
        fetch_data (bool): Whether to fetch data from the API. If False, will use existing intermediate files.
        generate_substitutions (bool): Whether to generate substitutions from fetched data. If False, will use existing substitutions_output.json if available.
        run_ue (bool): Whether to execute the Unreal headless step. If False, will skip Unreal processing.
        split_fbx (bool): Whether to parse substitutions and split FBX files for Unreal.
    """

    base_dir = os.path.dirname(os.path.abspath(__file__))
    unreal_ready_dir = os.path.join(base_dir, "jobs", "unreal_ready")
    inter_dir = os.path.join(base_dir, "jobs", "intermediate")
    unreal_output_dir = os.path.join(base_dir, "jobs", "unreal_out")

    os.makedirs(inter_dir, exist_ok=True)
    os.makedirs(unreal_ready_dir, exist_ok=True)
    os.makedirs(unreal_output_dir, exist_ok=True)

    print(f"Base directory: {base_dir}")
    print(f"Intermediate directory: {inter_dir}")
    print(f"Unreal directory: {unreal_ready_dir}")
    print(f"Output directory: {unreal_output_dir}")

    glosses_output_path = os.path.join(inter_dir, "all_glosses.json")
    sentences_output_path = os.path.join(inter_dir, "all_sentences.json")
    job_tracker_path = os.path.join(inter_dir, "job_tracker.json")
    glosses_variants_output_path = os.path.join(inter_dir, "base_variants_map.json")
    substitutions_output_path = os.path.join(unreal_ready_dir, "substitutions_output.json")

    # Ensure job tracker is initialized before any processing
    populate_job_tracker(job_tracker_path)

    if fetch_data:
        print(f"Step 1: Fetching glosses and sentences from the API...")
        run_fetch(
            glosses_output=glosses_output_path,
            glosses_variants_output=glosses_variants_output_path,
            sentences_output=sentences_output_path,
            job_tracker_output=job_tracker_path,
            limit=100
        )
    else:
        if not os.path.exists(glosses_output_path) or not os.path.exists(sentences_output_path):
            raise FileNotFoundError(f"Intermediate files not found. Run with --skip-fetching to skip fetching, but ensure that '{glosses_output_path}' and '{sentences_output_path}' exist.")
        print(f"Using existing intermediate files: '{glosses_output_path}' and '{sentences_output_path}'")

    if generate_substitutions:
        print(f"\nStep 2: Generating substitutions from fetched data...")
        generate_sentence_substitutions(
            glosses_file=glosses_output_path,
            sentences_file=sentences_output_path,
            output_file=substitutions_output_path,
        )
    else:
        if not os.path.exists(substitutions_output_path):
            raise FileNotFoundError(f"Substitutions file not found: {substitutions_output_path}. "
                                    f"Run with --generate-substitutions to create it.")
        print(f"Using existing substitutions file: {substitutions_output_path}")

    if split_fbx:
        print(f"\nStep 3: Parsing substitutions and splitting FBX files for Unreal...")
        run_parse_split(
            substitutions_file=substitutions_output_path,
            glosses_variants_map=glosses_variants_output_path,
            output_dir=unreal_ready_dir
        )
    else:
        print(f"Skipping parsing and splitting of FBX files.")

    if run_ue:
        print(f"\nStep 4: Executing headless Unreal processing...")
        run_unreal_headless(unreal_jobs_dir=unreal_ready_dir, unreal_output_dir=unreal_output_dir)
    else:
        print(f"Skipping Unreal headless execution.")

   
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full data fetching and processing pipeline.")
    parser.add_argument(
        "--skip-fetching",
        action="store_true",
        help="Skip fetching data from the API. Use existing intermediate files if available."
    )
    parser.add_argument(
        "--skip-substitutions",
        action="store_true",
        help="Skip generating substitutions from fetched data. If not set, will reuse existing substitutions_output.json if available."
    )
    parser.add_argument(
        "--skip-splitting",
        action="store_true",
        help="Skip parsing substitutions and splitting FBX files for Unreal. Use existing unreal_ready files if available."
    )
    parser.add_argument(
        "--skip-unreal",
        action="store_true",
        help="Skip executing Unreal headless step."
    )
    args = parser.parse_args()
    run_pipeline(
        fetch_data=not args.skip_fetching,
        generate_substitutions=not args.skip_substitutions,
        run_ue=not args.skip_unreal,
        split_fbx=not args.skip_splitting
    )