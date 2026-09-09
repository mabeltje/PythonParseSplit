from typing import cast

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

    # new_sequence, result = unreal.SequencerAbstractionBPLibrary.create_level_sequence_asset(
    #     "/Game/Sequences", "NewSequence")

    # if not new_sequence:
    #     unreal.log_error("[Headless Pipeline] New sequence is None after creation.")
    #     sys.exit(1)

    # if not result.success:
    #     unreal.log_error(f"[Headless Pipeline] Failed to create level sequence asset: {result.error}")
    #     sys.exit(1)

    # unreal.log(f"[Headless Pipeline] Created new level sequence asset: {new_sequence}")

    level_sequence = unreal.SequencerAbstractionBPLibrary.load_level_sequence_asset("/Game/LevelSequences/start_sequence")
    
    if not level_sequence:
        unreal.log_error("[Headless Pipeline] Failed to load level sequence asset: /Game/Sequences/start_sequence")
        sys.exit(1)

    unreal.log(f"[Headless Pipeline] Loaded level sequence asset: {level_sequence}")

    for job in job_data:
        unreal.log(f"[Headless Pipeline] Processing job: {job}")
        original_animation = job.get('original_animation')

        for sub in job.get('substitutions'):
            label = sub.get('label')
            index = sub.get('index')

            unreal.log(f"[Headless Pipeline] Executing substitution: {original_animation} -> {label} (index: {index})")

            # find file that starts with original)animation and ends with .srt
            srt_file = [f for f in os.listdir(os.path.join(job_dir, original_animation)) if f.startswith(original_animation) and f.endswith('.srt')]
            fbx_file = [f for f in os.listdir(os.path.join(job_dir, original_animation)) if f.startswith(original_animation) and f.endswith('.fbx')]

            original_animation_path = os.path.join(job_dir, original_animation, fbx_file[0])
            original_animation_srt_path = os.path.join(job_dir, original_animation, srt_file[0])
            donor_animation_path = os.path.join(job_dir, original_animation, f"{label}_TRIMMED.fbx")

            result = unreal.BlendingAutomationBFL.process_animation_substitution(
                level_sequence, original_animation_path, original_animation_srt_path, donor_animation_path, label, index)

            unreal.log(f"[Headless Pipeline] Substitution result: {result}")

    unreal.log("[Headless Pipeline] Unreal batch task complete. Exiting...")
    sys.exit(0)

if __name__ == "__main__":
    main()
