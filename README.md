# Python FBX Animation Pipeline

This repository prepares sign-language animation jobs for Unreal Engine. It fetches animation metadata and sentences, generates gloss substitutions, downloads and trims donor FBX files, and processes ready jobs in Unreal Engine.

The overall flow is documented in [Dataflow.md](Dataflow.md).

## Requirements

- Windows
- Python 3.11
- `requests`
- Autodesk FBX Python SDK, including the native `fbx` module for the selected Python version and architecture
- Unreal Engine 5.7, with a project containing the level sequence expected by `ue_process_jobs.py`
- Access to `https://signcollect.nl/blendBaking/api.php`
- An LLM endpoint configured in `DataGenerationBluey/bluey.json` when generating substitutions

The repository contains the helper `DataFetch/fbx_sdk/FbxCommon.py`. Install [FBX Python SDK downloads]([url](https://aps.autodesk.com/developer/overview/fbx-sdk)) for Python version 3.11.

Install the Python dependency with:

```powershell
python -m pip install requests
```

With importing of the FBX files into Unreal Engine, there is a bug in the Interchange pipeline that withholds the FBX import from happening with the old FBX importer. The function used to import the FBX file is written for the old importer. To work around this, disable the Interchange plugins in the Unreal project settings.

## Project Layout

```text
pipeline_runner.py                 Fetch data and prepare FBX jobs
DataGenerationBluey/               Fetch source data and generate substitutions
DataFetch/                         Download, trim, and organize FBX jobs
jobs/intermediate/                 Generated gloss and sentence JSON files
jobs/unreal_ready/                 Jobs prepared for Unreal processing
ue_process_jobs.py                 Unreal Python batch-processing script
Dataflow.md                        Pipeline diagram
```

## Configuration

Before running the full pipeline, update the Unreal paths near the top of `pipeline_runner.py`:

```python
UE_CMD_PATH = "C:/Program Files/Epic Games/UE_5.7/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
UPROJECT_PATH = "C:/Users/visualisationLab/Documents/Unreal Projects/BlendingAutomation/BlendingAutomation.uproject"
```

When using the LLM substitution step, configure the API URL, headers, and request data in `DataGenerationBluey/bluey.json`. That file is not currently included in the repository, so create it before using the LLM scripts. Do not commit credentials to that file.

The runner processes 10 sentences/jobs per stage by default. Use `-l` or `--limit` to change the batch size and `-s` or `--steps` to choose which stages run. Available steps are `setup`, `fetch`, `substitute`, `split`, and `unreal`.

## Run the Full Pipeline

From the repository root, run with Python version 3.11 (in a venv) for the FBX SDK animation trimming to work.

```powershell
python pipeline_runner.py
```

With no options, all five steps run in order: `setup`, `fetch`, `substitute`, `split`, and `unreal`.

To run only the preparation steps and skip Unreal:

```powershell
python pipeline_runner.py --steps setup fetch substitute split
```

To run only the substitution and split steps with a limit of five jobs per stage:

```powershell
python pipeline_runner.py --steps substitute split --limit 5
```

The `--limit` value applies to each selected stage. The Unreal step runs `UnrealEditor-Cmd.exe` headlessly and passes `jobs/unreal_ready` through the `UE_JOBS_DIR` environment variable. It expects `/Game/LevelSequences/start_sequence` to exist in the Unreal project.


## Outputs and Troubleshooting

- `jobs/intermediate/all_glosses.json` and `all_sentences.json` contain data fetched from the BlendBaking API.
- `jobs/unreal_ready/substitutions_output.json` contains the substitution definitions consumed by the preparation step.
- Each animation folder under `jobs/unreal_ready/` contains the original animation and downloaded SRT metadata. Trimmed donor FBX files are stored in the shared `jobs/unreal_ready/trimmed_fbx_cache/` directory.
- If the runner reports a missing Unreal executable or project, correct `UE_CMD_PATH` and `UPROJECT_PATH`.
- If substitution generation fails, create and check the endpoint configuration in `DataGenerationBluey/bluey.json` and verify the returned response format.
- If trimming fails, confirm that the FBX contains animation keys within the requested time window and that the FBX SDK matches the active Python installation.
