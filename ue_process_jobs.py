import unreal
import sys
import os
import json

def main():
    job_dir = os.environ.get("UE_JOBS_DIR")
    unreal.log(f"[Headless Pipeline] Received jobs directory: {job_dir}")

    if not job_dir or not os.path.exists(job_dir):
        unreal.log_error(f"[Headless Pipeline] Invalid jobs directory: {job_dir}")
        sys.exit(1)

    json_path = os.path.join(job_dir, "substitutions_output.json")
    if not os.path.exists(json_path):
        unreal.log_error(f"[Headless Pipeline] File not found: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        job_data = json.load(f)

    unreal.log(f"[Headless Pipeline] Loaded {len(job_data)} animation definitions to process.")

    # Call your C++ UBlueprintFunctionLibrary or Editor Utility here:
    # Example:
    # unreal.YourPluginFunctionLibrary.process_sign_blending_batch(json_path, job_dir)

    for job in job_data:
        # Here you would call the actual processing function for each job
        # For demonstration, we just log the job details
        unreal.log(f"[Headless Pipeline] Processing job: {job}")
        unreal.log(f"[Headless Pipeline] Processing animation: {job.get('original_animation')}, substitutions: {job.get('substitutions')}")

    unreal.log("[Headless Pipeline] Unreal batch task complete. Exiting...")
    unreal.UVTTParser.UVTTParser(None, None, None, None)
    sys.exit(0)

if __name__ == "__main__":
    main()