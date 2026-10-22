import os
import json
from pathlib import Path
import sys

"""
This module handles parsing the substitutions JSON, downloading the base animations and glosses, 
trimming the FBX files, and organizing the deliverables into the specified output directory.
"""

# Ensure project root (PythonParseSplit) is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Handle both direct execution (py parse_split.py) and package imports
from DataFetch.trim_fbx import trim_fbx_file
from DataFetch.call_api import download_single_gloss, download_batch

MODULE_DIR = Path(__file__).resolve().parent

def parse_json(file_path: str | Path, glosses_variants_map: str | Path, output_dir: str | Path) -> Path:
    """
    Parses substitutions JSON, downloads the base animations and glosses,
    trims the files, and organizes deliverables into output_dir.
    """
    json_path = Path(file_path).resolve()

    # Ensure output directory exists
    if not Path(output_dir).exists():
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    base_out_dir = Path(output_dir).resolve()

    # Make a directory for trimmed FBX file in the output directory
    trimmed_fbx_dir = base_out_dir / "trimmed_fbx_cache"
    trimmed_fbx_dir.mkdir(parents=True, exist_ok=True)
    trimmed_fbx_dir = trimmed_fbx_dir.resolve()

    if not json_path.is_file():
        raise FileNotFoundError(f"Substitutions file not found: {json_path}")
 
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(Path(glosses_variants_map).resolve(), "r", encoding="utf-8") as f:
        variants_map = json.load(f)

    # Process each sentence in the JSON data
    for sentence in data:
        original_animation = sentence.get("original_animation")
        substitutions = sentence.get("substitutions", [])

        if not original_animation:
            continue

        # Destination folder for this specific animation set
        anim_folder = base_out_dir / original_animation
        anim_folder.mkdir(parents=True, exist_ok=True)

        print(f"Preprocessing base: {original_animation}")
        download_batch([original_animation], output_dir=str(anim_folder))

        for sub in substitutions:
            gloss = sub.get("label")
            
            if not gloss:
                continue

            # Look up the gloss in the keys of the variants_map to find the corresponding base animation
            # go through the variants_map to find the base gloss 
            base_gloss = None
            for base, variants in variants_map.items():
                if gloss == base or gloss in variants:
                    base_gloss = base
                    break
            if not base_gloss:
                print(f"Gloss '{gloss}' not found in variants mapping. Skipping.")
                continue

            # Check if the trimmed FBX already exists to avoid redundant processing
            out_path = trimmed_fbx_dir / f"{gloss}_TRIMMED.fbx"
            if f"{gloss}_TRIMMED.fbx" in os.listdir(trimmed_fbx_dir):
                print(f"Trimmed FBX for gloss '{gloss}' already exists. Skipping trimming.")
                continue

            item = download_single_gloss(gloss, base_gloss, output_dir=str(anim_folder))
        
            if not item:
                print(f"Failed to download gloss '{gloss}'")
                continue

            start_time = item.get("start")
            end_time = item.get("end")
            fbx_path = item.get("fbx_path")
            success, error = trim_fbx_file(str(fbx_path), start_time, end_time, str(out_path))
            
            if not success:
                print(f"Error trimming FBX for gloss '{gloss}': {error}")
            else:
                print(f"Finished trimming FBX for gloss '{gloss}'")

            # Clean up un-trimmed source file
            if fbx_path and os.path.exists(fbx_path):
                os.remove(fbx_path)

        print(f"Finished preprocessing base: {original_animation}\n")

    return base_out_dir
   

def run_parse_split(substitutions_file: str | Path, glosses_variants_map: str | Path, output_dir: str | Path) -> Path:
    """Unified entry function for pipeline_runner.py"""
    return parse_json(file_path=substitutions_file, glosses_variants_map=glosses_variants_map, output_dir=output_dir)


if __name__ == "__main__":
    # Standalone test fallback pointing relative to project root
    project_root = MODULE_DIR.parent
    default_unreal_ready = project_root / "jobs" / "unreal_ready"
    default_unreal_inter = project_root / "jobs" / "intermediate"

    run_parse_split(
        substitutions_file=default_unreal_ready / "substitutions_output.json",
        glosses_variants_map=default_unreal_inter / "base_variants_map.json",
        output_dir=default_unreal_ready
    )
