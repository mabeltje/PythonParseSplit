from email.mime import text
from typing import cast

import unreal
import sys
import os
import json

def log_header(text: str):
    unreal.log(f"[Headless Pipeline] {'=' * 70}")
    unreal.log(f"[Headless Pipeline]   {text}")
    unreal.log(f"[Headless Pipeline] {'=' * 60}")

def main():
    job_dir = os.environ.get("UE_JOBS_DIR")
    # unreal.log(f"[Headless Pipeline] Received jobs directory: {job_dir}")

    if not job_dir or not os.path.exists(job_dir):
        unreal.log_error(f"[Headless Pipeline] Invalid jobs directory: {job_dir}")
        sys.exit(1)

    json_path = os.path.join(job_dir, "substitutions_output.json")
    if not os.path.exists(json_path):
        unreal.log_error(f"[Headless Pipeline] File not found: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        job_data = json.load(f)

    unreal.log(f"[Headless Pipeline] Starting Unreal Headless Pipeline: {len(job_data)} sentences to process")

    level_sequence = unreal.SequencerAbstractionBPLibrary.load_level_sequence_asset("/Game/LevelSequences/start_sequence")
    
    if not level_sequence:
        unreal.log_error("[Headless Pipeline] Failed to load level sequence asset: /Game/Sequences/start_sequence")
        sys.exit(1)

    # unreal.log(f"[Headless Pipeline] Loaded  the level sequence asset")

    for job in job_data:
        job_index = job_data.index(job) + 1
        log_header(f"Processing job {job_index}/{len(job_data)}: '{job.get('original_animation')}' with {len(job.get('substitutions'))} substitution(s)")
        original_animation = job.get('original_animation')

        for sub in job.get('substitutions'):
            label = sub.get('label')
            index = sub.get('index')
            
            # Find file that starts with original)animation and ends with .srt
            srt_file = [f for f in os.listdir(os.path.join(job_dir, original_animation)) if f.startswith(original_animation) and f.endswith('.srt')]
            fbx_file = [f for f in os.listdir(os.path.join(job_dir, original_animation)) if f.startswith(original_animation) and f.endswith('.fbx')]

            original_animation_path = os.path.join(job_dir, original_animation, fbx_file[0])
            original_animation_srt_path = os.path.join(job_dir, original_animation, srt_file[0])
            donor_animation_path = os.path.join(job_dir, original_animation, f"{label}_TRIMMED.fbx")

            # print the paths for debugging
            # unreal.log(f"[Headless Pipeline] Original animation path: {original_animation_path}")
            # unreal.log(f"[Headless Pipeline] Original animation SRT path: {original_animation_srt_path}")
            # unreal.log(f"[Headless Pipeline] Donor animation path: {donor_animation_path}")
            result = unreal.BlendingAutomationBFL.process_animation_substitution(
                level_sequence, original_animation_path, original_animation_srt_path, donor_animation_path, label, index)

            # unreal.log(f"[Headless Pipeline] Substitution result: {result}")

    unreal.log("[Headless Pipeline] Unreal batch task complete. Exiting...")
    sys.exit(0)

if __name__ == "__main__":
    main()
