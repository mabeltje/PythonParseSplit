import os
import json
from trim_fbx import trim_fbx_file
from call_api import download_single_gloss, download_batch


def parse_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)

    # process for each sentence in the JSON data
    for sentence in data:
        original_animation = sentence.get('original_animation')
        substitutions = sentence.get('substitutions', [])

        print(f"Processing base: {original_animation}")
        download_batch([original_animation], output_dir="jobs")

        for sub in substitutions:
            gloss = sub.get('label')

            item = download_single_gloss(gloss, output_dir="jobs/" + original_animation)
            start_time = item.get('start')
            end_time = item.get('end')
            fbx_path = item.get('fbx_path')

            out_path = os.path.join("jobs/", original_animation, f"{gloss}_TRIMMED.fbx")
            succes, error = trim_fbx_file(fbx_path, start_time, end_time, out_path)
            if not succes:
                print(f"Error trimming FBX for gloss '{gloss}': {error}")

            print(f"Finished trimming FBX for gloss '{gloss}'")

            if os.path.exists(fbx_path):
                os.remove(fbx_path)
                print(f"Deleted original FBX file: {fbx_path}")

        print(f"Finished processing base: {original_animation}\n")

           

def main():
    # Define the path to the JSON file
    json_file_path = os.path.join(os.path.dirname(__file__), 'substitutions.json')

    # Parse the JSON file
    parse_json(json_file_path)


if __name__ == "__main__":
    main()
