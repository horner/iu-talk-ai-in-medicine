#!/usr/bin/env python3
"""
Analyze frames from video to find spreadsheet and analysis content.
Uses fast ImageMagick analysis + smarter classification.
"""
import subprocess
import os

FRAMES_DIR = "/Volumes/Case/prj/iu-talk/frames"
VIDEO = "/Volumes/Case/prj/iu-talk/Video by jackiebrenner.mp4"
OUTPUT_DIR = "/Volumes/Case/prj/iu-talk/screenshots"

def get_frame_stats(fname):
    """Get brightness and color stats quickly using convert."""
    r = subprocess.run(
        ["convert", fname, "-colorspace", "Gray", "-format",
         "%[fx:mean] %[fx:standard_deviation] %[fx:maxima] %[fx:minima]", "info:"],
        capture_output=True, text=True, timeout=10
    )
    parts = r.stdout.strip().split()
    if len(parts) >= 4:
        mean_b = float(parts[0])
        std_b = float(parts[1])
        max_b = float(parts[2])
        min_b = float(parts[3])
    else:
        mean_b = std_b = max_b = min_b = 0

    # Get saturation info (spreadsheets are low saturation, charts may be high)
    r2 = subprocess.run(
        ["convert", fname, "-colorspace", "HSL", "-channel", "G",
         "-separate", "-format", "%[fx:mean] %[fx:standard_deviation]", "info:"],
        capture_output=True, text=True, timeout=10
    )
    parts2 = r2.stdout.strip().split()
    if len(parts2) >= 2:
        mean_sat = float(parts2[0])
        std_sat = float(parts2[1])
    else:
        mean_sat = std_sat = 0

    return {
        "brightness": mean_b,
        "brightness_std": std_b,
        "brightness_max": max_b,
        "brightness_min": min_b,
        "saturation": mean_sat,
        "saturation_std": std_sat,
    }

def extract_high_quality_frame(video, timestamp_sec, output_path):
    """Extract a single high-quality frame from the video."""
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(timestamp_sec),
        "-i", video,
        "-frames:v", "1",
        "-q:v", "1",
        output_path
    ], capture_output=True, timeout=15)

def main():
    print("Analyzing all 90 frames (fast mode)...")
    results = []
    for i in range(1, 91):
        fname = os.path.join(FRAMES_DIR, f"frame_{i:04d}.jpg")
        if not os.path.exists(fname):
            continue
        stats = get_frame_stats(fname)
        timestamp = (i - 1) * 2
        r = {"index": i, "fname": fname, "timestamp": timestamp, **stats}
        results.append(r)
        flag = ""
        if stats["brightness"] > 0.65:
            flag = " *** BRIGHT (potential screen content)"
        elif stats["brightness"] > 0.55:
            flag = " ** moderately bright"
        print(f"  Frame {i:04d} (t={timestamp:3d}s): "
              f"bright={stats['brightness']:.3f} std={stats['brightness_std']:.3f} "
              f"sat={stats['saturation']:.3f} sat_std={stats['saturation_std']:.3f}"
              f"{flag}")

    print("\n" + "="*60)

    # Sort by brightness to see the distribution
    sorted_by_bright = sorted(results, key=lambda x: -x["brightness"])
    print("\nTop 20 brightest frames:")
    for r in sorted_by_bright[:20]:
        print(f"  Frame {r['index']:04d} at {r['timestamp']:3d}s: "
              f"brightness={r['brightness']:.3f} saturation={r['saturation']:.3f}")

    print("\nDarkest 10 frames:")
    for r in sorted_by_bright[-10:]:
        print(f"  Frame {r['index']:04d} at {r['timestamp']:3d}s: "
              f"brightness={r['brightness']:.3f} saturation={r['saturation']:.3f}")

    # Classify based on brightness + saturation patterns observed:
    # - Talking head: brightness < 0.55, saturation > 0.20
    # - Spreadsheet: brightness > 0.55, saturation < 0.13  
    # - Analysis/charts: brightness > 0.55, saturation 0.13-0.22
    # - Mixed/transition: everything else
    
    spreadsheet_frames = []
    analysis_frames = []
    screen_frames = []

    for r in results:
        b = r["brightness"]
        s = r["saturation"]
        if b > 0.55 and s < 0.13:
            spreadsheet_frames.append(r)
            screen_frames.append(r)
        elif b > 0.55 and s < 0.22:
            analysis_frames.append(r)
            screen_frames.append(r)
    
    print(f"\nFound {len(screen_frames)} screen content frames total")

    print(f"\n  Spreadsheet-like: {len(spreadsheet_frames)} frames")
    for r in spreadsheet_frames:
        print(f"    Frame {r['index']:04d} at {r['timestamp']}s")
    print(f"\n  Analysis/chart-like: {len(analysis_frames)} frames")
    for r in analysis_frames:
        print(f"    Frame {r['index']:04d} at {r['timestamp']}s")

    # Create output directories
    os.makedirs(os.path.join(OUTPUT_DIR, "spreadsheets"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "analysis"), exist_ok=True)

    def deduplicate(frames, min_gap=6):
        """Keep frames that represent distinct scenes."""
        if not frames:
            return []
        frames = sorted(frames, key=lambda x: x["timestamp"])
        deduped = [frames[0]]
        for f in frames[1:]:
            prev = deduped[-1]
            time_gap = f["timestamp"] - prev["timestamp"]
            # Detect scene change: significant shift in brightness or saturation
            bright_diff = abs(f["brightness"] - prev["brightness"])
            sat_diff = abs(f["saturation"] - prev["saturation"])
            scene_change = bright_diff > 0.03 or sat_diff > 0.03
            
            if time_gap >= min_gap and scene_change:
                deduped.append(f)
            elif time_gap >= min_gap * 2:
                # Keep even if similar, if time gap is large
                deduped.append(f)
            elif time_gap < min_gap:
                # Within gap - keep brighter one
                if f["brightness"] > prev["brightness"]:
                    deduped[-1] = f
        return deduped

    spreadsheet_deduped = deduplicate(spreadsheet_frames)
    analysis_deduped = deduplicate(analysis_frames)

    print(f"\nAfter dedup: {len(spreadsheet_deduped)} spreadsheet, {len(analysis_deduped)} analysis")

    # If few screen frames detected, also extract top brightest as candidates
    all_screen = spreadsheet_deduped + analysis_deduped
    if len(all_screen) < 3:
        print("\nFew screen frames detected. Also extracting top 15 brightest as candidates...")
        candidates = deduplicate(sorted_by_bright[:15], min_gap=4)
        for r in candidates:
            out = os.path.join(OUTPUT_DIR, f"candidate_t{r['timestamp']:03d}s_f{r['index']:04d}.jpg")
            extract_high_quality_frame(VIDEO, r["timestamp"], out)
            print(f"  Saved: {out}")

    # Extract spreadsheet frames
    print(f"\nExtracting {len(spreadsheet_deduped)} spreadsheet screenshots...")
    for j, r in enumerate(spreadsheet_deduped, 1):
        out = os.path.join(OUTPUT_DIR, "spreadsheets",
                          f"spreadsheet_{j:02d}_t{r['timestamp']:03d}s.jpg")
        extract_high_quality_frame(VIDEO, r["timestamp"], out)
        print(f"  Saved: {out}")

    # Extract analysis frames
    print(f"\nExtracting {len(analysis_deduped)} analysis screenshots...")
    for j, r in enumerate(analysis_deduped, 1):
        out = os.path.join(OUTPUT_DIR, "analysis",
                          f"analysis_{j:02d}_t{r['timestamp']:03d}s.jpg")
        extract_high_quality_frame(VIDEO, r["timestamp"], out)
        print(f"  Saved: {out}")

    print("\nDone! Check the screenshots/ directory.")

if __name__ == "__main__":
    main()
