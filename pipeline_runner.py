import os
import argparse
import subprocess


# Import modular steps
from DataGenerationBluey.fetch_data_bluey import run_fetch
from DataGenerationBluey.generate_substitutions import run_generate
from DataFetch.parse_split import run_parse_split

UE_CMD_PATH = "C:/Program Files/Epic Games/UE_5.7/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
UPROJECT_PATH = "C:/Users/visualisationLab/Documents/Unreal Projects/BlendingAutomation/BlendingAutomation.uproject"

def run_unreal_headless(unreal_jobs_dir: str):
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
        "-FullStdOutLogOutput",
        f"-jobs_dir={unreal_jobs_dir}"  # Custom argument passed to the UE script
    ]

    # print(f"\n[Unreal] Launching headless Unreal Engine instance...")
    # result = subprocess.run(cmd, capture_output=True, text=True)

    # if result.returncode != 0:
    #     print(f"[Unreal Error] Unreal exited with code {result.returncode}")
    #     print(result.stderr)
    # else:
    #     print("[Unreal] Unreal process finished successfully!")

    # Pass the jobs directory via environment variables
    env = os.environ.copy()
    env["UE_JOBS_DIR"] = os.path.abspath(unreal_jobs_dir)

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
    "LogPython: Warning:"

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


def run_pipeline(generate_substitutions: bool = False, run_ue: bool = True):
    """
    Runs the data fetching and saving pipeline to get all the data ready for Unreal.
    :param generate_substitutions: If True, will generate substitutions from the fetched data.
    If False, reuses existing substitutions_output.json if available.
    """

    base_dir = os.path.dirname(os.path.abspath(__file__))
    unreal_ready_dir = os.path.join(base_dir, "jobs", "unreal_ready")
    inter_dir = os.path.join(base_dir, "jobs", "intermediate")

    os.makedirs(inter_dir, exist_ok=True)
    os.makedirs(unreal_ready_dir, exist_ok=True)

    print(f"Base directory: {base_dir}")
    print(f"Intermediate directory: {inter_dir}")
    print(f"Unreal directory: {unreal_ready_dir}")

    glosses_output_path = os.path.join(inter_dir, "all_glosses.json")
    sentences_output_path = os.path.join(inter_dir, "all_sentences.json")
    substitutions_output_path = os.path.join(unreal_ready_dir, "substitutions_output.json")
    rules_json = os.path.join(base_dir, "DataGenerationBluey", "rules.json")

    print(f"Step 1: Fetching glosses and sentences from the API...")
    run_fetch(
        glosses_output=glosses_output_path,
        sentences_output=sentences_output_path,
        page=3,
        limit=2
    )

    print(f"\nStep 2: Generating substitutions from fetched data...")
    if generate_substitutions:
        run_generate(
            glosses_file=glosses_output_path,
            sentences_file=sentences_output_path,
            output_file=substitutions_output_path,
            rules_file=rules_json
        )
    else:
        if not os.path.exists(substitutions_output_path):
            raise FileNotFoundError(f"Substitutions file not found: {substitutions_output_path}. "
                                    f"Run with --generate-substitutions to create it.")
        print(f"Using existing substitutions file: {substitutions_output_path}")

    print(f"\nStep 3: Parsing substitutions and splitting FBX files for Unreal...")
    run_parse_split(
        substitutions_file=substitutions_output_path,
        output_dir=unreal_ready_dir
    )

    print(f"\nStep 4: Executing headless Unreal processing...")
    if run_ue:
        run_unreal_headless(unreal_jobs_dir=unreal_ready_dir)

   
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full data fetching and processing pipeline.")
    parser.add_argument(
        "--generate-substitutions",
        action="store_true",
        help="Generate substitutions from fetched data. If not set, will reuse existing substitutions_output.json if available."
    )
    parser.add_argument(
        "--skip-unreal",
        action="store_true",
        help="Skip executing Unreal headless step."
    )
    args = parser.parse_args()
    run_pipeline(generate_substitutions=args.generate_substitutions, run_ue=not args.skip_unreal)