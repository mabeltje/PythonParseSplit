import os
import re
import yaml
from trim_fbx import trim_fbx_file

def parse_custom_srt(srt_path):
    """Parses custom metadata and subtitle entries from the SRT file."""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    metadata = {}
    parts = content.split('---', 2)
    if len(parts) < 3:
        raise ValueError("SRT file does not contain expected metadata and subtitle sections.")

    metadata = yaml.safe_load(parts[1])

    return metadata

def update_srt_status(srt_path, status='trimmed'):
    """Updates the YAML metadata frontmatter in the SRT file cleanly using pyyaml."""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    parts = content.split('---', 2)
    if len(parts) < 3:
        print(f"Error updating '{srt_path}': File missing YAML frontmatter structure.")
        return False

    metadata = yaml.safe_load(parts[1]) or {}
    metadata['phase'] = status
    updated_yaml = yaml.dump(metadata, sort_keys=False, default_flow_style=False).strip()
    updated_content = f"---\n{updated_yaml}\n---{parts[2]}"

    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print(f"Successfully updated metadata in '{srt_path}'.")
    return True
    
if __name__ == '__main__':
    # Example usage
    srt_path = r"C:\Users\visualisationLab\Documents\PythonParseSplit\example_animation_set\goal_anim.srt"
    example_donor_path = r"C:\Users\visualisationLab\Documents\PythonParseSplit\example_animation_set\donor\M20260127_2280_260319_0.fbx"

    metadata = parse_custom_srt(srt_path)
    label = metadata['substitution']['label']
    output_folder = r"C:\Users\visualisationLab\Documents\PythonParseSplit\example_animation_set"

    if metadata.get('phase') == 'trimmed' or os.path.exists(os.path.join(output_folder, f"{label}_trimmed.fbx")):
        print(f"Animation for label '{label}' has already been trimmed. Skipping trimming step.")
        update_srt_status(srt_path, status='trimmed')
        exit(0)
    else:
        print(f"Trimming animation for label '{label}' from {metadata['trim_start']} to {metadata['trim_end']} seconds.")
    
    success, error = trim_fbx_file(
        fbx_path=example_donor_path,
        start_time=metadata['trim_start'],
        end_time=metadata['trim_end'],
        out_path=os.path.join(output_folder, f"{label}_trimmed.fbx"),
        note="Trimmed from call_api pipeline"
    )

    if success:
        print("Trimming completed successfully.")
        update_srt_status(srt_path)
    else:
        print(f"Trimming failed: {error}")
        update_srt_status(srt_path, status='error')

    
