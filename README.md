# Python FBX Animation Pipeline

This project prepares Dutch Sign Language (NGT) animation jobs for Unreal
Engine. It fetches source data, generates gloss substitutions, downloads and
trims donor FBX files, and runs Unreal Engine headlessly to produce blended
animation output.

The high-level workflow is documented in [Dataflow.md](Dataflow.md).

## Requirements

### Operating system and Python

- Windows
- Python 3.11 (in a virtual environment)
- Access to the BlendBaking API:
  `https://signcollect.nl/blendBaking/api.php`


#### Python dependencies

- `requests`
- `openai`
- `python-dotenv`

The following command installs the required packages:

```powershell
python -m pip install requests openai python-dotenv
```

### Autodesk FBX SDK

Autodesk FBX Python SDK, including the native fbx module for the selected Python version and architecture.
The preparation stage imports Autodesk's native `fbx` module to inspect, trim,
and export FBX animation files.

- [Autodesk FBX SDK downloads](https://aps.autodesk.com/developer/overview/fbx-sdk)
- Install FBX Python SDK downloads for Python version 3.11.
<!-- - The native `fbx` module must be importable by the selected Python
  interpreter. -->
- The repository contains the helper DataFetch/fbx_sdk/FbxCommon.py.


### Unreal Engine Project Setup

- Unreal Engine 5.7
- A compatible Unreal project called `BlendingAutomation` (`BlendingAutomation.uproject`) (see [Unreal Project Setup](#unreal-project-setup))
- `UnrealEditor-Cmd.exe` available on disk


#### Plugins 

- [Unreal VTT Parser](https://github.com/mabeltje/UnrealVTTParser)
- [Sequencer Abstraction](https://github.com/J-Andersen-UvA/sequencerAbstraction)
- [Unreal Asset File Management](https://github.com/J-Andersen-UvA/UnrealAssetFileManagement)
- Interchange FBX Importer: This project uses the legacy FBX importer, disable all the Interchange plugins in Edit > Plugins to prevent the Interchange FBX Importer from being used. 

#### C++ Modules

[Unreal Headless Module](https://github.com/mabeltje/UnrealHeadlessModule): Clone into `Source/BlendingAutomationEditor` and register the module in your `.uproject` and `Editor.Target.cs` files before building. See the module's README for instructions on setting up the module and Project.

#### Unreal Project Setup

- A level sequence at `/Game/LevelSequences/start_sequence`
- An actor that is compatible with the animations used
- Create a `SkeletalSequenceDataAsset` at **`/Game/Config/AutomationConfig`** and assign its values (more info in the [Unreal Headless Module README](https://github.com/mabeltje/UnrealHeadlessModule))


### LLM credentials

The substitution stage uses the UvA OpenAI-compatible proxy configured in
`DataGenerationBluey/bluey_LLM.py`. Create a `.env` file in the repository
root with:

```text
UVA_LLM_KEY=your-key-here
```

Do NOT commit `.env` or credentials. The current pipeline runner does not use
`DataGenerationBluey/bluey.json` for its LLM configuration.

## Getting started

Clone the repository and create an environment:

```powershell
git clone https://github.com/mabeltje/PythonParseSplit.git
cd PythonParseSplit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install requests openai python-dotenv
```

Install and verify the FBX SDK for the active Python 3.11 interpreter, create
the `.env` file if using substitutions, and configure the Unreal paths in
`pipeline_runner.py`:

```python
UE_CMD_PATH = "C:/Program Files/Epic Games/UE_5.7/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
UPROJECT_PATH = "C:/Users/visualisationLab/Documents/Unreal Projects/BlendingAutomation/BlendingAutomation.uproject"
```

The runner creates these directories automatically:

- `jobs/intermediate`
- `jobs/unreal_ready`
- `jobs/unreal_out`

## Pipeline stages

The runner supports five stages. They normally run in this order:

| Stage | Description | Tracker transition |
| --- | --- | --- |
| `setup` | Fetch glosses and gloss variants, then add available base animations to the tracker | New jobs become `PENDING` |
| `fetch` | Fetch sentence and subtitle data for pending jobs | `PENDING` -> `LLM_READY` |
| `substitute` | Send eligible sentences and glosses to the LLM | `LLM_READY` -> `LLM_DONE` |
| `split` | Download source and donor animations, trim donor FBX files, and prepare Unreal jobs | `LLM_DONE` -> `UNREAL_READY` |
| `unreal` | Run Unreal Engine headlessly for prepared jobs | `UNREAL_READY` -> `UNREAL_DONE` |

The tracker is stored in `jobs/intermediate/job_tracker.json`. Running only
later stages is supported, but the required earlier-stage files and tracker
statuses must already exist.

## Usage

To set up the correct environment and fetch the required data, follow these steps:

```powershell
python pipeline_runner.py --steps setup
```

Run all stages with the default limit of 10 jobs per stage:

```powershell
python pipeline_runner.py
```

Show the current command-line options:

```powershell
python pipeline_runner.py --help
```

The runner supports:

```text
-l, --limit       Number of sentences/jobs processed by each selected stage
-s, --steps       One or more of: setup fetch substitute split unreal
```

Run only the preparation stages and skip Unreal:

```powershell
python pipeline_runner.py --steps fetch substitute split
```

Run a smaller batch. The limit applies independently to every selected stage:

```powershell
python pipeline_runner.py --steps fetch substitute split --limit 5
```

Run Unreal only for jobs already marked `UNREAL_READY`:

```powershell
python pipeline_runner.py --steps unreal --limit 10
```

## Unreal processing

Before the `unreal` stage, the runner writes the selected ready jobs to:

```text
jobs/unreal_ready/substitutions_output.json
```

It launches `UnrealEditor-Cmd.exe` with `ue_process_jobs.py` and sets:

- `UE_JOBS_DIR` to `jobs/unreal_ready`
- `UE_OUTPUT_DIR` to `jobs/unreal_out`

The Unreal script loads `/Game/LevelSequences/start_sequence`, processes each
substitution, and writes blended output beneath
`jobs/unreal_out/<original-animation>/`. Donor SRT export files are written
into the corresponding `jobs/unreal_ready/<base-id>/` folder.


## Generated files

- `jobs/intermediate/all_glosses.json`: gloss and sense data from the API.
- `jobs/intermediate/base_variants_map.json`: base gloss to variant mapping.
- `jobs/intermediate/job_tracker.json`: job inputs, substitutions, and statuses.
- `jobs/unreal_ready/<base-id>/`: downloaded source animation and SRT files.
- `jobs/unreal_ready/trimmed_fbx_cache/`: cached trimmed donor FBX files.
- `jobs/unreal_ready/substitutions_output.json`: jobs supplied to Unreal.
- `jobs/unreal_out/<base-id>/`: blended output generated by Unreal.

