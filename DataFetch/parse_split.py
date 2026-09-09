import os
import json
from pathlib import Path

# Handle imports whether executed directly or imported from pipeline_runner
try:
    from trim_fbx import trim_fbx_file
    from call_api import download_single_gloss, download_batch
except ImportError:
    from DataFetch.trim_fbx import trim_fbx_file
    from DataFetch.call_api import download_single_gloss, download_batch

MODULE_DIR = Path(__file__).resolve().parent

def parse_json(file_path: str | Path, output_dir: str | Path) -> Path:
    """
    Parses substitutions JSON, downloads the base animations and glosses,
    trims the files, and organizes deliverables into output_dir.
    """
    json_path = Path(file_path).resolve()

    # Ensure output directory exists
    if not Path(output_dir).exists():
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    base_out_dir = Path(output_dir).resolve()

    if not json_path.is_file():
        raise FileNotFoundError(f"Substitutions file not found: {json_path}")
 
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

   # Process each sentence in the JSON data
    for sentence in data:
        original_animation = sentence.get("original_animation")
        substitutions = sentence.get("substitutions", [])

        if not original_animation:
            continue

        # Destination folder for this specific animation set
        anim_folder = base_out_dir / original_animation
        anim_folder.mkdir(parents=True, exist_ok=True)

        print(f"Processing base: {original_animation}")
        download_batch([original_animation], output_dir=str(anim_folder))

        for sub in substitutions:
            gloss = sub.get("label")
            if not gloss:
                continue

            item = download_single_gloss(gloss, output_dir=str(anim_folder))

            if not item:
                print(f"Failed to download gloss '{gloss}'")
                continue

            start_time = item.get("start")
            end_time = item.get("end")
            fbx_path = item.get("fbx_path")

            out_path = anim_folder / f"{gloss}_TRIMMED.fbx"
            success, error = trim_fbx_file(fbx_path, start_time, end_time, str(out_path))
            

            if not success:
                print(f"Error trimming FBX for gloss '{gloss}': {error}")
            else:
                print(f"Finished trimming FBX for gloss '{gloss}'")

            # Clean up un-trimmed source file
            if fbx_path and os.path.exists(fbx_path):
                os.remove(fbx_path)
                print(f"Deleted original FBX file: {fbx_path}")

        print(f"Finished processing base: {original_animation}\n")

    return base_out_dir
   

def run_parse_split(substitutions_file: str | Path, output_dir: str | Path) -> Path:
    """Unified entry function for pipeline_runner.py"""
    return parse_json(file_path=substitutions_file, output_dir=output_dir)


if __name__ == "__main__":
    # Standalone test fallback pointing relative to project root
    project_root = MODULE_DIR.parent
    default_unreal_ready = project_root / "jobs" / "unreal_ready"

    run_parse_split(
        substitutions_file=default_unreal_ready / "substitutions_output.json",
        output_dir=default_unreal_ready
    )
