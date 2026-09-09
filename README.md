# Python FBX Animation Pipeline

This repository prepares sign-language animation jobs for Unreal Engine. It fetches animation metadata, generates gloss substitutions, downloads and trims donor FBX files, and optionally sends the prepared jobs to Unreal for blending.

The overall flow is documented in [Dataflow.md](Dataflow.md).

## Requirements

- Windows
- Python 3.9 or newer
- `requests`
- Autodesk FBX Python SDK, including the native `fbx` module for the selected Python version and architecture
- Unreal Engine 5.7, with a project containing the level sequence expected by `ue_process_jobs.py`
- Access to `https://signcollect.nl/blendBaking/api.php`
- An LLM endpoint configured in `DataGenerationBluey/bluey.json` when generating substitutions

The repository contains the helper `DataFetch/fbx_sdk/FbxCommon.py`, but it does not contain the FBX SDK's native Python bindings. Install those separately and make sure they are importable by `DataFetch/trim_fbx.py`.

Install the Python dependency with:

```powershell
python -m pip install requests
```

## Project Layout

```text
pipeline_runner.py                 Run the complete fetch-to-Unreal pipeline
DataGenerationBluey/               Fetch source data and generate substitutions
DataFetch/                         Download, trim, and organize FBX jobs
jobs/intermediate/                 Generated gloss and sentence JSON files
jobs/unreal_ready/                 Jobs prepared for Unreal processing
Animations/                        Manually downloaded animation assets
ue_process_jobs.py                 Unreal Python batch-processing script
Dataflow.md                        Pipeline diagram
```

## Configuration

Before running the full pipeline, update the Unreal paths near the top of `pipeline_runner.py`:

```python
UE_CMD_PATH = "C:/Program Files/Epic Games/UE_5.7/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
UPROJECT_PATH = "C:/Users/visualisationLab/Documents/Unreal Projects/BlendingAutomation/BlendingAutomation.uproject"
```

When using the LLM substitution step, configure the API URL, headers, and request data in `DataGenerationBluey/bluey.json`. Do not commit credentials to that file.

The default fetch currently requests page 3 with a limit of 2. Change the `page` and `limit` arguments in `pipeline_runner.py` if a different batch is required.

## Run the Full Pipeline

From the repository root:

```powershell
python pipeline_runner.py --skip-unreal
```

This fetches glosses and sentences, reuses the existing `jobs/unreal_ready/substitutions_output.json`, downloads the required source and donor animations, trims the donor FBX files, and creates Unreal-ready job folders.

To generate a new substitution file through the configured LLM endpoint:

```powershell
python pipeline_runner.py --generate-substitutions --skip-unreal
```

To run the Unreal batch step as well, omit `--skip-unreal`:

```powershell
python pipeline_runner.py --generate-substitutions
```

The Unreal step runs `UnrealEditor-Cmd.exe` headlessly and passes `jobs/unreal_ready` through the `UE_JOBS_DIR` environment variable. It expects `/Game/LevelSequences/start_sequence` to exist in the Unreal project.

## Trim an FBX Directly

For a single animation, use `DataFetch/trim_fbx.py`:

```powershell
python DataFetch/trim_fbx.py `
  --fbx "Animations\input.fbx" `
  --start "00:00:01,718" `
  --end "00:00:03,842" `
  --note "Trimmed sign segment" `
  --out "Animations\trimmed_animation.fbx"
```

Start and end times accept seconds (`1.718`) or `HH:MM:SS,mmm` / `HH:MM:SS.mmm`. The script reads the FBX frame rate, snaps the boundaries to frame boundaries, removes keys outside the window, shifts the remaining animation to start at zero, and embeds trim metadata in the output FBX.

## Outputs and Troubleshooting

- `jobs/intermediate/all_glosses.json` and `all_sentences.json` contain data fetched from the BlendBaking API.
- `jobs/unreal_ready/substitutions_output.json` contains the substitution definitions consumed by the preparation step.
- Each folder under `jobs/unreal_ready/` contains the original animation, downloaded SRT metadata, and trimmed donor FBX files.
- If the runner reports a missing Unreal executable or project, correct `UE_CMD_PATH` and `UPROJECT_PATH`.
- If substitution generation fails, check the endpoint configuration in `DataGenerationBluey/bluey.json` and the returned response format.
- If trimming fails, confirm that the FBX contains animation keys within the requested time window and that the FBX SDK matches the active Python installation.
