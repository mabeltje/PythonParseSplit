# Python FBX Animation Parser and Splitter

Python utilities for downloading sign-language animation assets, reading custom SRT metadata, and trimming FBX animation clips.

## Requirements

- Windows (the current example paths and SDK loading are Windows-oriented)
- Python 3.9 or newer
- `requests`
- `PyYAML`
- Autodesk FBX Python SDK for the Python version you are using

The repository includes `fbx_sdk/FbxCommon.py`, but the `fbx` Python module and its native FBX SDK libraries must also be installed. The FBX SDK must be compatible with your Python version and architecture.

## Project Layout

```text
call_api.py                         Download FBX/SRT pairs from signcollect.nl
trim_fbx.py                         Trim one FBX animation from a time window
parse_split.py                      Read SRT YAML metadata and run a trim
fbx_sdk/FbxCommon.py                Local FBX SDK helper module
example_animation_set/              Example SRT and input/output location
Animations/                         Downloaded animation assets
```

### 1. Download animation assets

Edit `BASE_CODES`, `OUTPUT_DIR`, or `API_URL` in `call_api.py` if needed, then run:

```powershell
python call_api.py
```

The script requests timing data from the configured API and saves each returned FBX and SRT file under `Animations/<base-code>/`.

### 2. Trim an FBX directly

Use `trim_fbx.py` when you already know the source FBX and time window:

```powershell
python trim_fbx.py `
  --fbx "Animations\M20260127_2280\input.fbx" `
  --start "00:00:01,718" `
  --end "00:00:03,842" `
  --note "Trimmed sign segment" `
  --out "Animations\M20260127_2280\trimmed_animation.fbx"
```

Start and end times accept either seconds (`1.718`) or `HH:MM:SS,mmm` / `HH:MM:SS.mmm`. The script reads the FBX frame rate, snaps the boundaries to frame boundaries, removes keys outside the window, shifts the remaining animation to start at zero, and writes trim metadata into the output FBX.

### 3. Run the SRT-driven example pipeline

`parse_split.py` reads the YAML frontmatter in `example_animation_set/goal_anim.srt`. Before running it, update these paths in the `__main__` block if your files are elsewhere:

- `srt_path`: the goal SRT file
- `example_donor_path`: the donor FBX to trim
- `output_folder`: where the trimmed FBX is written

The SRT must contain these fields:

```yaml
substitution:
  label: MORGEN-A
trim_start: 00:00:01,234
trim_end: 00:00:01,340
phase: pending
```

Run it with:

```powershell
python parse_split.py
```

On success, the pipeline writes `<label>_trimmed.fbx` to the output folder and changes the SRT `phase` to `trimmed`. If no keys are found or trimming fails, it sets the phase to `error`.

## Notes

- `parse_split.py` expects a donor FBX file; the example SRT alone is not sufficient to run the trim.
- Re-running the SRT pipeline skips an animation when its phase is already `trimmed` or the expected trimmed output already exists.
- Keep downloaded FBX files and generated outputs backed up before running scripts that modify SRT metadata.
- The API and download URLs used by `call_api.py` must be available on your network.
