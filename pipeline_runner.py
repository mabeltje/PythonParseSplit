import os
import argparse


# Import modular steps
from DataGenerationBluey.fetch_data_bluey import run_fetch
from DataGenerationBluey.generate_substitutions import run_generate
from DataFetch.parse_split import run_parse_split

UE_CMD_PATH = "C:/Program Files/Epic Games/UE_5.3/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
# UPROJECT_PATH = 


def run_pipeline(generate_substitutions: bool = False):
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

# def prepare_unreal_manifest(substitutions_file: str | Path, unreal_ready_dir: str | Path) -> Path:
#     """
#     Scans substitutions_output.json and maps each sentence to its corresponding
#     downloaded base FBX and trimmed substitution FBXs.
#     """
#     substitutions_path = Path(substitutions_file).resolve()
#     unreal_dir = Path(unreal_ready_dir).resolve()
    
#     with open(substitutions_path, "r", encoding="utf-8") as f:
#         sentences_data = json.load(f)

    # manifest_tasks = []

    # for index, item in enumerate(sentences_data):
    #     base_name = item.get("original_animation")
    #     sentence_text = item.get("zin", "")
    #     raw_glosses = item.get("glosses", [])
    #     substitutions = item.get("substitutions", [])

    #     # The base animation directory created by parse_split.py
    #     anim_folder = unreal_dir / base_name
    #     base_fbx = anim_folder / f"{base_name}.fbx"

    #     # Collect trimmed substitution FBXs
    #     sub_list = []
    #     for sub in substitutions:
    #         label = sub.get("label")
    #         trimmed_fbx = anim_folder / f"{label}_TRIMMED.fbx"
            
    #         sub_list.append({
    #             "label": label,
    #             "fbx_path": str(trimmed_fbx),
    #             "exists": trimmed_fbx.exists()
    #         })

    #     task_entry = {
    #         "task_id": f"sentence_{index:03d}",
    #         "base_animation_name": base_name,
    #         "base_fbx_path": str(base_fbx),
    #         "sentence_text": sentence_text,
    #         "glosses": raw_glosses,
    #         "substitutions": sub_list
    #     }
    #     manifest_tasks.append(task_entry)

    # manifest_file = unreal_dir / "unreal_task_manifest.json"
    # with open(manifest_file, "w", encoding="utf-8") as f:
    #     json.dump({"tasks": manifest_tasks}, f, indent=2, ensure_ascii=False)

    # print(f"\n[Step 4] Unreal task manifest generated with {len(manifest_tasks)} tasks at: {manifest_file}")
    # return manifest_file

   
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full data fetching and processing pipeline.")
    parser.add_argument(
        "--generate-substitutions",
        action="store_true",
        help="Generate substitutions from fetched data. If not set, will reuse existing substitutions_output.json if available."
    )
    args = parser.parse_args()
    run_pipeline(generate_substitutions=args.generate_substitutions)