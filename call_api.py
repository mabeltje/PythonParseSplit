import os
import requests

# Base codes you want to download
BASE_CODES = ["M20260224_5441", "M20260127_2280"]

# Target output directory (points directly to your Unreal Project directory or external folder)
OUTPUT_DIR = r"C:\Users\visualisationLab\Documents\PythonParseSplit\Animations"

API_URL = "https://signcollect.nl/blendBaking/api.php"

def download_batch(codes, output_dir):
    for base in codes:
        print(f"Processing {base}...")
        
        # Create folder for code
        target_folder = os.path.join(output_dir, base)
        os.makedirs(target_folder, exist_ok=True)
        
        # 1. Fetch JSON timings
        r = requests.get(API_URL, params={'action': 'timings', 'base': base})
        data = r.json()
        
        if not data.get('success') or not data.get('sentences'):
            print(f"Skipping {base}: {data.get('error', 'No data found')}")
            continue
            
        sentence = data['sentences'][0]
        fbx_url = sentence['fbxUrl']
        srt_url = sentence['srtUrl']
        
        # Download FBX file
        fbx_name = fbx_url.split('/')[-1]
        fbx_path = os.path.join(target_folder, fbx_name)
        
        fbx_data = requests.get(fbx_url).content
        with open(fbx_path, 'wb') as f:
            f.write(fbx_data)

        # Download SRT file
        srt_name = srt_url.split('/')[-1]
        srt_path = os.path.join(target_folder, srt_name)

        srt_data = requests.get(srt_url).content
        with open(srt_path, 'wb') as f:
            f.write(srt_data)

        print(f"Successfully saved {base} -> {target_folder}")


# Download a single gloss and its associated FBX file
def download_single_gloss(gloss, output_dir):

    # Fetch max 5 instances of the gloss across all sentences
    r = requests.get(API_URL, params={'action': 'timings', 'gloss': gloss, 'limit':5})
    data = r.json()

    if not data.get('success') or not data.get('sentences'):
        print(f"Skipping gloss '{gloss}': {data.get('error', 'No data found')}")
        return

    print(f"Found {len(data['sentences'])} sentence(s) containing gloss '{gloss}'.")

    # Get glosses for the first sentence by default for now
    sentence = data['sentences'][0]
    glosses = sentence['glosses']
    fbx_url = sentence['fbxUrl']
    base = sentence['base']

    # Find the specific gloss info
    gloss_info = next(g for g in glosses if g['baseGloss'] == gloss)

    if gloss_info:
        print(f"Found gloss '{gloss}' in base '{base}': {gloss_info}")

        gloss_start = gloss_info['start']
        gloss_end = gloss_info['end']

    # Create folder for the base code
    target_folder = os.path.join(output_dir, base)
    os.makedirs(target_folder, exist_ok=True)
    
    # Download FBX file
    fbx_name = fbx_url.split('/')[-1]
    fbx_path = os.path.join(target_folder, fbx_name)
    fbx_data = requests.get(fbx_url).content
    with open(fbx_path, 'wb') as f:
        f.write(fbx_data)

    return {
        'base': base,
        'gloss': gloss,
        'start': gloss_start,
        'end': gloss_end,
        'fbx_path': fbx_path
    }


def main():
    # download_batch(BASE_CODES, OUTPUT_DIR)
    download_single_gloss("WIE", OUTPUT_DIR)

if __name__ == "__main__":
    main()

