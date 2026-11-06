import os
import requests

API_URL = "https://signcollect.nl/blendBaking/api.php"

def get_senses(gloss):
    """
    Fetches the senses for a given gloss from the API.
    """
    response = requests.get(API_URL, params={'action': 'senses', 'gloss': gloss})
    data = response.json()

    if not data.get('success'):
        raise ValueError(f"API Error: {data.get('error', 'Unknown error')}")
    
    return data.get('senses', [])


def download_batch(codes, output_dir):
    """
    Downloads FBX and SRT files for a batch of base animation codes.
    """
    for base in codes:
        os.makedirs(output_dir, exist_ok=True)
        
        # Fetch JSON timings
        r = requests.get(API_URL, params={'action': 'timings', 'base': base})
        data = r.json()
        
        if not data.get('success') or not data.get('sentences'):
            print(f"Skipping {base}: {data.get('error', 'No data found')}")
            continue
   
        sentence = data['sentences'][0]
        fbx_url = sentence['fbxUrl']
        srt_url = sentence['srtUrl']

        # Check if fbx_url and srt_url are valid
        if not fbx_url or not srt_url:
            print(f"Skipping {base}: Missing FBX or SRT URL.")
            continue
        
        # Download FBX file
        fbx_name = fbx_url.split('/')[-1]
        fbx_path = os.path.join(output_dir, fbx_name)
        
        fbx_data = requests.get(fbx_url).content
        with open(fbx_path, 'wb') as f:
            f.write(fbx_data)

        # Download SRT file
        srt_name = srt_url.split('/')[-1]
        srt_path = os.path.join(output_dir, srt_name)

        srt_data = requests.get(srt_url).content
        with open(srt_path, 'wb') as f:
            f.write(srt_data)

        print(f"Successfully saved {base} -> {output_dir}")


def download_single_gloss(gloss, base_gloss, output_dir):
    """
    Downloads the FBX file for a specific gloss and its corresponding base gloss.
    Returns a dictionary containing the base, gloss, start time, end time, and the path to the downloaded FBX file.
    """
    # Fetch the first sentence that contains the gloss
    r = requests.get(API_URL, params={'action': 'timings', 'gloss': base_gloss})
    data = r.json()

    if not data.get('success') or not data.get('sentences'):
        print(f"Skipping gloss '{gloss}': {data.get('error', 'No data found')}")
        return

    # Loop over sentences to find the one that contains the correct gloss
    sentence = None
    for s in data['sentences']:
        if any(g['gloss'] == gloss for g in s['glosses']):
            sentence = s
            break

    if not sentence:
        print(f"Skipping gloss '{gloss}': No sentence found containing this gloss.")
        return

    glosses = sentence['glosses']
    fbx_url = sentence['fbxUrl']
    base = sentence['base']

    # Find the specific gloss info
    gloss_info = next(g for g in glosses if g['baseGloss'] == base_gloss)

    if gloss_info:
        gloss_start = gloss_info['start']
        gloss_end = gloss_info['end']

    # Download FBX file
    fbx_name = gloss + "_" + fbx_url.split('/')[-1]

    fbx_path = os.path.join(output_dir, fbx_name)
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
