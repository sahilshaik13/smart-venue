import json
import os
from collections import defaultdict

def summarize_scene(name, file_path, max_lines=100000):
    print(f"Summarizing {name}...")
    tracks = defaultdict(list)
    
    with open(file_path, "r") as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            parts = line.strip().split(" ")
            if len(parts) < 10:
                continue
                
            track_id = parts[0]
            xmin = int(parts[1])
            ymin = int(parts[2])
            frame_id = int(parts[5])
            label = parts[9].strip('"')
            
            # Subsample frames to keep JSON small
            if frame_id % 10 == 0:
                tracks[track_id].append({
                    "f": frame_id,
                    "x": xmin,
                    "y": ymin,
                    "t": label
                })
                
    # Filter for quality tracks (long paths)
    active_tracks = {tid: pts for tid, pts in tracks.items() if len(pts) > 10}
    
    # Take a hero subset (top 50)
    hero_ids = list(active_tracks.keys())[:50]
    return {tid: active_tracks[tid] for tid in hero_ids}

def main():
    root = "D:/promptwars/data/raw/archive_1/annotations"
    scenes = {
        "plaza": os.path.join(root, "deathCircle/video0/annotations.txt"),
        "arena": os.path.join(root, "nexus/video0/annotations.txt"),
        "aeros": os.path.join(root, "bookstore/video0/annotations.txt")
    }
    
    patterns = {}
    for name, path in scenes.items():
        if os.path.exists(path):
            patterns[name] = summarize_scene(name, path)
        else:
            print(f"Skipping {name}, path not found: {path}")
            
    output_path = "D:/promptwars/backend/app/resources/hero_patterns.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(patterns, f)
    print(f"Saved {len(patterns)} scenes to {output_path}")

if __name__ == "__main__":
    main()
