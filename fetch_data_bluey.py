import json
import requests

# API endpoint
API_URL = "https://signcollect.nl/blendBaking/api.php"

def fetch_and_save_glosses(filename):
    # Define request parameters
    params = {
        "action": "glosses"
    }

    try:
        # Make the GET request
        response = requests.get(API_URL, params=params)
        response.raise_for_status()  # Check for network/HTTP errors
        
        data = response.json()

        # The API returns HTTP 200 even on error, so check the "success" key
        if isinstance(data, dict) and not data.get("success", True):
            raise ValueError(f"API Error: {data.get('error', 'Unknown error')}")
        
  
        data = list(data["bases"].keys())  # Extract the list of glosses

        # Save to JSON file with clean formatting and UTF-8 encoding
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"Successfully saved glosses to '{filename}'")

    except requests.exceptions.RequestException as e:
        print(f"Network error occurred: {e}")
    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def fetch_and_save_sentences(filename):
    # Define request parameters
    params = {
        "action": "timings",
        "limit": 5
    }

    try:
        # Make the GET request
        response = requests.get(API_URL, params=params)
        response.raise_for_status()  # Check for network/HTTP errors
        
        data = response.json()

        # The API returns HTTP 200 even on error, so check the "success" key
        if isinstance(data, dict) and not data.get("success", True):
            raise ValueError(f"API Error: {data.get('error', 'Unknown error')}")
        

        output_data = []
        sentences = data["sentences"]

        # Transform each sentence to your target structure
        for sentence in sentences:
            formatted_item = {
                "original_animation": sentence.get("base", ""),
                "glosses": [g.get("gloss") for g in sentence.get("glosses", [])],
                "zin": sentence.get("zin", ""),
                "substitutions": []
            }
            output_data.append(formatted_item)


        # Save to JSON file with clean formatting and UTF-8 encoding
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        print(f"Successfully saved sentences to '{filename}'")

    except requests.exceptions.RequestException as e:
        print(f"Network error occurred: {e}")
    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # fetch_and_save_glosses("all_glosses.json")
    fetch_and_save_sentences("all_sentences.json")