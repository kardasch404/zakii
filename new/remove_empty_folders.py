#!/usr/bin/env python3
"""Remove empty journalist folders"""
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "muckrack" / "datamuckrack"

def main():
    print("\n" + "="*80)
    print("🧹 REMOVING EMPTY FOLDERS")
    print("="*80 + "\n")
    
    removed_count = 0
    
    # Scan all location directories
    for location_dir in DATA_DIR.glob("*"):
        if not location_dir.is_dir():
            continue
        
        # Check each journalist folder
        for journalist_dir in location_dir.glob("*"):
            if not journalist_dir.is_dir():
                continue
            
            # Check if folder is empty (no files)
            files = list(journalist_dir.glob("*"))
            
            if len(files) == 0:
                # Folder is completely empty
                try:
                    journalist_dir.rmdir()
                    print(f"🗑️  Removed: {location_dir.name}/{journalist_dir.name}")
                    removed_count += 1
                except Exception as e:
                    print(f"❌ Error removing {journalist_dir}: {e}")
    
    print("\n" + "="*80)
    print(f"✅ Removed {removed_count:,} empty folders")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
