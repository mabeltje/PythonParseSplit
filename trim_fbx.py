#!/usr/bin/env python3
import sys
import argparse
import os

# Tell Python to search the fbx_sdk subfolder for modules
SDK_PATH = os.path.join(os.path.dirname(__file__), 'fbx_sdk')
if SDK_PATH not in sys.path:
    sys.path.insert(0, SDK_PATH)

import FbxCommon
from fbx import FbxAnimStack, FbxAnimLayer, FbxTime, FbxTimeSpan, FbxDocumentInfo

"""
Trim a single FBX animation to a specific start and end timestamp window,
normalize the resulting keyframes to start at t = 0.0s, snap to frame boundaries,
and embed trim metadata.

Usage:
  python trim_fbx.py \
    --fbx animation.fbx \
    --start 00:00:01,718 \
    --end 00:00:03,842 \
    --note "Trimmed sign segment" \
    --out trimmed_animation.fbx
"""

def load_scene(path):
    manager, scene = FbxCommon.InitializeSdkObjects()
    if not FbxCommon.LoadScene(manager, scene, path):
        print(f"Failed to load {path}")
        sys.exit(1)
    return manager, scene


def save_scene(manager, scene, out_path):
    exporter = FbxCommon.FbxExporter.Create(manager, "")
    ios = manager.GetIOSettings()
    exporter.Initialize(out_path, -1, ios)
    exporter.Export(scene)
    exporter.Destroy()


def parse_timestamp(time_str):
    """Converts 'HH:MM:SS,mmm', 'HH:MM:SS.mmm', or float strings to total seconds."""
    if isinstance(time_str, (int, float)):
        return float(time_str)
    
    clean_str = str(time_str).strip().replace(',', '.')
    
    if ':' in clean_str:
        parts = clean_str.split(':')
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return hours * 3600.0 + minutes * 60.0 + seconds
    
    return float(clean_str)


def snap_to_frame_boundary(time_sec, fps=24.0):
    """Snaps a timestamp in seconds to the nearest whole frame boundary at target FPS."""
    frame_number = round(time_sec * fps)
    return frame_number / fps


def trim_and_shift_scene(scene, start_sec, end_sec):
    start_time = FbxTime(); start_time.SetSecondDouble(start_sec)
    end_time = FbxTime();   end_time.SetSecondDouble(end_sec)

    try:
        # 1. Verify animation stacks exist
        anim_stacks = [scene.GetSrcObject(i) for i in range(scene.GetSrcObjectCount()) 
                       if isinstance(scene.GetSrcObject(i), FbxAnimStack)]
        if not anim_stacks:
            return False, "No FbxAnimStack found in scene."

        keys_retained = 0

        for src in anim_stacks:
            scene.SetCurrentAnimationStack(src)

            def recurse(node):
                nonlocal keys_retained
                for prop in (node.LclTranslation, node.LclRotation, node.LclScaling):
                    for j in range(src.GetMemberCount()):
                        layer = src.GetMember(j)
                        if not isinstance(layer, FbxAnimLayer):
                            continue
                        
                        for axis in ('X', 'Y', 'Z'):
                            curve = prop.GetCurve(layer, axis)
                            if not curve:
                                continue

                            curve.KeyModifyBegin()
                            
                            # Remove keyframes outside window
                            to_del = [k for k in range(curve.KeyGetCount())
                                      if (curve.KeyGetTime(k) < start_time or
                                          curve.KeyGetTime(k) > end_time)]
                            for k in reversed(to_del):
                                curve.KeyRemove(k)

                            retained_count = curve.KeyGetCount()
                            keys_retained += retained_count

                            # Shift remaining keyframes to t = 0.0s
                            for k in range(retained_count):
                                orig_time = curve.KeyGetTime(k)
                                new_time = FbxTime()
                                new_time.SetSecondDouble(orig_time.GetSecondDouble() - start_sec)
                                curve.KeySetTime(k, new_time)

                            curve.KeyModifyEnd()

                for idx in range(node.GetChildCount()):
                    recurse(node.GetChild(idx))

            recurse(scene.GetRootNode())

        # Check if any keyframes actually fell within the window
        if keys_retained == 0:
            return False, f"No keyframes found in window [{start_sec:.3f}s -> {end_sec:.3f}s]."

        # Update Animation Stack Local Time Span
        duration_sec = end_sec - start_sec
        new_start_time = FbxTime(); new_start_time.SetSecondDouble(0.0)
        new_end_time = FbxTime();   new_end_time.SetSecondDouble(duration_sec)

        for src in anim_stacks:
            span = FbxTimeSpan()
            span.Set(new_start_time, new_end_time)
            src.SetLocalTimeSpan(span)

        return True, None

    except Exception as e:
        return False, str(e)

def embed_metadata(manager, scene, start_sec, end_sec, note=None):
    doc_info = FbxDocumentInfo.Create(manager, "TrimMetadata")
    doc_info.mTitle = "Trimmed Animation Segment"
    doc_info.mSubject = f"Original Window: {start_sec:.3f}s - {end_sec:.3f}s"
    if note:
        doc_info.mComment = note
    scene.SetSceneInfo(doc_info)

def get_scene_fps(scene, default_fps=30.0):
    """Reads the frame rate setting directly from the FBX global settings."""
    global_settings = scene.GetGlobalSettings()
    time_mode = global_settings.GetTimeMode()
    fps = FbxTime.GetFrameRate(time_mode)
    
    return float(fps) if fps > 0 else default_fps

def trim_fbx_file(fbx_path, start_time, end_time, out_path, note=None):
    try:
        raw_start = parse_timestamp(start_time)
        raw_end = parse_timestamp(end_time)

        manager, scene = load_scene(fbx_path)
        if not scene:
            return False, f"Failed to load FBX: {fbx_path}"

        fps = get_scene_fps(scene)
        start_sec = snap_to_frame_boundary(raw_start, fps)
        end_sec = snap_to_frame_boundary(raw_end, fps)

        if start_sec >= end_sec:
            return False, f"Start time ({start_sec}s) >= end time ({end_sec}s)"

        # Run trim
        success, error = trim_and_shift_scene(scene, start_sec, end_sec)
        if not success:
            manager.Destroy()
            return False, error

        embed_metadata(manager, scene, start_sec, end_sec, note)
        save_scene(manager, scene, out_path)
        manager.Destroy()

        return True, None  # Success!

    except Exception as e:
        return False, str(e)


def main():
    p = argparse.ArgumentParser(description='Trim FBX animation to timestamps, zero-align start, and snap frames.')
    p.add_argument('--fbx',   required=True, help='Input FBX file')
    p.add_argument('--start', required=True, type=parse_timestamp, help='Start time (e.g. 0.972 or 00:00:00,972)')
    p.add_argument('--end',   required=True, type=parse_timestamp, help='End time (e.g. 3.842 or 00:00:03,842)')
    p.add_argument('--note',  help='Optional comment/note to embed in FBX metadata')
    p.add_argument('--out',   required=True, help='Output FBX path')
    args = p.parse_args()

    trim_fbx_file(
        fbx_path=args.fbx,
        start_time=args.start,
        end_time=args.end,
        out_path=args.out,
        note=args.note
    )


if __name__ == '__main__':
    main()