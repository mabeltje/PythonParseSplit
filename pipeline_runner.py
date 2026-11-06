import argparse
import json
import os
import subprocess

from DataFetch.parse_split import run_parse_split
from DataGenerationBluey.fetch_data_bluey import run_fetch_setup, run_fetch_sentences
from DataGenerationBluey.generate_substitutions import generate_sentence_substitutions
from DataGenerationBluey.job_tracker import populate_job_tracker, update_job

UE_CMD_PATH = "C:/Program Files/Epic Games/UE_5.7/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
UPROJECT_PATH = "C:/Users/visualisationLab/Documents/Unreal Projects/BlendingAutomation/BlendingAutomation.uproject"
API_URL = "https://signcollect.nl/blendBaking/api.php"


def run_unreal_headless(unreal_jobs_dir: str, unreal_output_dir: str, job_tracker_file: str, limit: int):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ue_script_path = os.path.join(base_dir, "ue_process_jobs.py")

    # Get the first 'limit' number of jobs that are marked as "UNREAL_READY" in the job tracker, also include the base_id in the output json
    with open(job_tracker_file, "r", encoding="utf-8") as f:
        job_tracker = json.load(f)
        unreal_ready_jobs = [
            {
                "original_animation": base_id,
                "nederlands_zin": job.get("input", {}).get("nederlands_zin", ""),
                "substitutions": job.get("substitutions", [])
            }
            for base_id, job in job_tracker.items()
            if job.get("status", {}) == "UNREAL_READY"
        ][:limit]
        
    with open(os.path.join(unreal_jobs_dir, "substitutions_output.json"), "w", encoding="utf-8") as f:
        json.dump(unreal_ready_jobs, f, ensure_ascii=False, indent=2)

    if not os.path.exists(UE_CMD_PATH):
        raise FileNotFoundError(f"UnrealEditor-Cmd not found at {UE_CMD_PATH}")
    if not os.path.exists(UPROJECT_PATH):
        raise FileNotFoundError(f".uproject not found at {UPROJECT_PATH}")
    if not os.path.exists(ue_script_path):
        raise FileNotFoundError(f"Unreal script not found at {ue_script_path}")

    cmd = [
        UE_CMD_PATH,
        UPROJECT_PATH,
        f"-ExecutePythonScript={ue_script_path}",
        "-nullrhi",
        "-nosound",
        "-nopause",
        "-unattended",
        "-stdout",
        "-FullStdOutLogOutput",
        f"-jobs_dir={unreal_jobs_dir}",
    ]

    # Pass the jobs directory via environment variables
    env = os.environ.copy()
    env["UE_JOBS_DIR"] = os.path.abspath(unreal_jobs_dir)
    env["UE_OUTPUT_DIR"] = os.path.abspath(unreal_output_dir)

    print(f"\n[Unreal] Launching headless Unreal Engine instance for batch of {len(unreal_ready_jobs)} jobs...")
    
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
        for job in unreal_ready_jobs:
            base_id = job.get("original_animation")
            update_job(job_tracker_file, base_id, status_update="UNREAL_DONE")
        print("\n[Unreal] Unreal process finished successfully!")


def run_pipeline(limit: int = 10, steps: list[str] = None):
    """
    Executes selected pipeline stages with specified batch limits.
    """
    if steps is None:
        steps = ["fetch", "substitute", "split", "unreal"]

    base_dir = os.path.dirname(os.path.abspath(__file__))
    unreal_ready_dir = os.path.join(base_dir, "jobs", "unreal_ready")
    inter_dir = os.path.join(base_dir, "jobs", "intermediate")
    unreal_output_dir = os.path.join(base_dir, "jobs", "unreal_out")

    os.makedirs(inter_dir, exist_ok=True)
    os.makedirs(unreal_ready_dir, exist_ok=True)
    os.makedirs(unreal_output_dir, exist_ok=True)

    glosses_output_path = os.path.join(inter_dir, "all_glosses.json")
    job_tracker_path = os.path.join(inter_dir, "job_tracker.json")
    glosses_variants_output_path = os.path.join(inter_dir, "base_variants_map.json")

    # TODO: move into setup step
    populate_job_tracker(job_tracker_path)

    print(f"\n--- Pipeline Run Config ---")
    print(f"Batch Limit: {limit}")
    print(f"Active Steps: {', '.join(steps)}")
    print(f"---------------------------\n")

    if "setup" in steps:
        print(f"[Step 1/5] Fetching glosses and gloss variants mapping...")
        run_fetch_setup(
            glosses_output=glosses_output_path,
            glosses_variants_output=glosses_variants_output_path
        )

    if "fetch" in steps:
        print(f"[Step 2/5] Fetching batch of sentences (Limit: {limit})...")
        run_fetch_sentences(
            job_tracker_output=job_tracker_path,
            limit=limit
        )
    if "substitute" in steps:
        print(f"\n[Step 3/5] Generating LLM substitutions (Limit: {limit})...")
        generate_sentence_substitutions(
            glosses_file=glosses_output_path,
            job_tracker_file=job_tracker_path,
            limit=limit
        )

    if "split" in steps:
        print(f"\n[Step 4/5] Parsing substitutions and splitting FBX files...")
        run_parse_split(
            glosses_variants_map=glosses_variants_output_path,
            job_tracker_file=job_tracker_path,
            unreal_ready_dir=unreal_ready_dir,
            limit=limit
        )

    if "unreal" in steps:
        print(f"\n[Step 5/5] Running Unreal Engine headless baking...")
        run_unreal_headless(
            unreal_jobs_dir=unreal_ready_dir,
            unreal_output_dir=unreal_output_dir,
            job_tracker_file=job_tracker_path,
            limit=limit
        )

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NGT Animation Blending Pipeline Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=10,
        help="Number of sentences/jobs to process per stage."
    )
    
    parser.add_argument(
        "-s", "--steps",
        nargs="+",
        choices=["setup", "fetch", "substitute", "split", "unreal"],
        default=["fetch", "substitute", "split", "unreal"],
        help="Specify which pipeline step(s) to execute."
    )

    args = parser.parse_args()
    run_pipeline(limit=args.limit, steps=args.steps)