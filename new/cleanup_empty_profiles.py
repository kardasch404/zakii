#!/usr/bin/env python3
"""Clean up empty journalist profiles and prepare for re-scraping"""
import json
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "muckrack" / "datamuckrack"
EMPTY_DIR = BASE_DIR / "muckrack" / "empty_profiles"
EMPTY_DIR.mkdir(parents=True, exist_ok=True)

def is_empty_profile(data):
    """Check if profile has no real data"""
    if not data.get('profile'):
        return True
    
    profile = data['profile']
    
    # Check if all important fields are empty
    checks = [
        not profile.get('avatar'),  # No avatar
        not profile.get('jobs') or len(profile.get('jobs', [])) == 0,  # No jobs
        not profile.get('location'),  # No location
        not profile.get('beats') or len(profile.get('beats', [])) == 0,  # No beats
        not profile.get('asSeenIn') or len(profile.get('asSeenIn', [])) == 0,  # No outlets
    ]
    
    # If 4 or more checks are True, consider it empty
    empty_count = sum(checks)
    return empty_count >= 4

def has_real_data(data):
    """Check if profile has real data"""
    if not data.get('profile'):
        return False
    
    profile = data['profile']
    
    # Has data if any of these exist
    has_data = [
        bool(profile.get('avatar')),
        bool(profile.get('jobs') and len(profile.get('jobs', [])) > 0),
        bool(profile.get('location')),
        bool(profile.get('beats') and len(profile.get('beats', [])) > 0),
        bool(profile.get('asSeenIn') and len(profile.get('asSeenIn', [])) > 0),
    ]
    
    # If 2 or more have data, keep it
    return sum(has_data) >= 2

def main():
    print("\n" + "="*80)
    print("🧹 CLEANING EMPTY PROFILES")
    print("="*80 + "\n")
    
    total_files = 0
    empty_profiles = 0
    good_profiles = 0
    moved_profiles = []
    
    # Scan all JSON files
    for json_file in DATA_DIR.rglob("*.json"):
        total_files += 1
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if empty
            if is_empty_profile(data):
                empty_profiles += 1
                
                # Get relative path
                rel_path = json_file.relative_to(DATA_DIR)
                location = rel_path.parts[0]
                name = rel_path.parts[1]
                
                # Create destination
                dest_dir = EMPTY_DIR / location / name
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = dest_dir / json_file.name
                
                # Move file
                shutil.move(str(json_file), str(dest_file))
                
                moved_profiles.append({
                    'name': name,
                    'location': location,
                    'url': data.get('url', ''),
                    'from': str(json_file),
                    'to': str(dest_file)
                })
                
                print(f"📦 Moved: {location}/{name}")
                
                # Remove empty journalist folder
                journalist_folder = json_file.parent
                try:
                    # Check if folder is empty
                    if journalist_folder.exists() and not any(journalist_folder.iterdir()):
                        journalist_folder.rmdir()
                        print(f"   🗑️  Removed empty folder: {journalist_folder.name}")
                except Exception as e:
                    print(f"   ⚠️  Could not remove folder: {e}")
                
            elif has_real_data(data):
                good_profiles += 1
                
        except Exception as e:
            print(f"❌ Error processing {json_file}: {e}")
    
    # Save report
    report_file = EMPTY_DIR / f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_scanned': total_files,
            'empty_profiles': empty_profiles,
            'good_profiles': good_profiles,
            'moved_profiles': moved_profiles
        }, f, indent=2, ensure_ascii=False)
    
    # Summary
    print("\n" + "="*80)
    print("📊 CLEANUP SUMMARY")
    print("="*80)
    print(f"📁 Total files scanned: {total_files:,}")
    print(f"✅ Good profiles (kept): {good_profiles:,}")
    print(f"📦 Empty profiles (moved): {empty_profiles:,}")
    print(f"📋 Report saved: {report_file}")
    print(f"📂 Empty profiles moved to: {EMPTY_DIR}")
    print("="*80 + "\n")
    
    # Show examples
    if moved_profiles:
        print("\n📋 Examples of moved profiles:")
        for profile in moved_profiles[:5]:
            print(f"  • {profile['location']}/{profile['name']}")
            print(f"    URL: {profile['url']}")
        
        if len(moved_profiles) > 5:
            print(f"  ... and {len(moved_profiles) - 5} more")
    
    print("\n💡 These profiles will be re-scraped on next run!")

if __name__ == "__main__":
    main()
