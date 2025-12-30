#!/usr/bin/env python3
"""Remove journalists with empty profile data"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'

def is_empty_profile(data):
    """Check if profile has meaningful data"""
    profile = data.get('profile', {})
    
    # Check if any important field has data
    has_data = (
        profile.get('avatar') or
        profile.get('jobs') or
        profile.get('location') or
        profile.get('beats') or
        profile.get('asSeenIn') or
        profile.get('socialHandles') or
        profile.get('covers') or
        profile.get('doesnt_cover') or
        profile.get('intro')
    )
    
    return not has_data

def clean_location(location_dir):
    """Remove empty profiles from a location directory"""
    removed = 0
    kept = 0
    
    # Check if files are directly in location_dir or in subdirectories
    json_files = list(location_dir.glob('*.json'))
    
    if not json_files:
        # Files are in subdirectories (one folder per journalist)
        for journalist_dir in location_dir.iterdir():
            if journalist_dir.is_dir():
                for file in journalist_dir.glob('*.json'):
                    try:
                        data = json.loads(file.read_text())
                        
                        if is_empty_profile(data):
                            # Remove the entire journalist directory
                            import shutil
                            shutil.rmtree(journalist_dir)
                            removed += 1
                            print(f"  ❌ Removed: {journalist_dir.name}")
                            break  # Only process first json file in dir
                        else:
                            kept += 1
                            break  # Only process first json file in dir
                    except Exception as e:
                        print(f"  ⚠️  Error processing {file.name}: {e}")
    else:
        # Files are directly in location_dir
        for file in json_files:
            try:
                data = json.loads(file.read_text())
                
                if is_empty_profile(data):
                    file.unlink()
                    removed += 1
                    print(f"  ❌ Removed: {file.name}")
                else:
                    kept += 1
            except Exception as e:
                print(f"  ⚠️  Error processing {file.name}: {e}")
    
    return removed, kept

def main():
    if not DATA_DIR.exists():
        print(f"❌ Directory not found: {DATA_DIR}")
        return
    
    total_removed = 0
    total_kept = 0
    
    for location_dir in sorted(DATA_DIR.iterdir()):
        if location_dir.is_dir():
            print(f"\n🔍 Cleaning {location_dir.name}...")
            removed, kept = clean_location(location_dir)
            total_removed += removed
            total_kept += kept
            print(f"  ✅ Kept: {kept}, Removed: {removed}")
    
    print(f"\n🎉 Done!")
    print(f"📊 Total kept: {total_kept}")
    print(f"🗑️  Total removed: {total_removed}")

if __name__ == '__main__':
    main()
