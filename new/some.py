#!/usr/bin/env python3
import json
import os
from pathlib import Path

# Path to locations directory
locations_dir = Path(__file__).parent.parent / "journalistv2" / "locations"

total = 0
locations = []

# Read all JSON files
for json_file in locations_dir.glob("*.json"):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        count = data.get("total_journalists", 0)
        location = data.get("location", json_file.stem)
        total += count
        locations.append((location, count))

# Sort by count descending
locations.sort(key=lambda x: x[1], reverse=True)

# Print results
print(f"Total journalists across all locations: {total:,}\n")
print(f"Breakdown by location ({len(locations)} locations):\n")
for location, count in locations:
    print(f"{location:30} {count:>10,}")
