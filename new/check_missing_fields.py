#!/usr/bin/env python3
"""Check which journalists are missing profile fields"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'

missing_fields = []
total = 0

for location_dir in sorted(DATA_DIR.glob('*')):
    if not location_dir.is_dir():
        continue
    
    for journalist_dir in location_dir.glob('*'):
        if not journalist_dir.is_dir():
            continue
        
        json_file = journalist_dir / f'{journalist_dir.name}.json'
        if not json_file.exists():
            continue
        
        total += 1
        try:
            data = json.loads(json_file.read_text())
            profile = data.get('profile', {})
            
            # Check for new fields
            has_pronouns = 'pronouns' in profile
            has_intro = 'intro' in profile
            has_covers = 'covers' in profile
            has_doesnt_cover = 'doesnt_cover' in profile
            
            if not all([has_pronouns, has_intro, has_covers, has_doesnt_cover]):
                missing_fields.append({
                    'location': location_dir.name,
                    'name': journalist_dir.name,
                    'missing': [f for f, v in [
                        ('pronouns', has_pronouns),
                        ('intro', has_intro),
                        ('covers', has_covers),
                        ('doesnt_cover', has_doesnt_cover)
                    ] if not v]
                })
        except:
            pass

print(f"📊 Total journalists: {total:,}")
print(f"❌ Missing fields: {len(missing_fields):,}")
print(f"✅ Complete: {total - len(missing_fields):,}")
print(f"\n📈 Completion: {((total - len(missing_fields)) / total * 100):.1f}%")

if missing_fields:
    print(f"\n🔍 Sample missing (first 10):")
    for item in missing_fields[:10]:
        print(f"  {item['location']}/{item['name']}: {', '.join(item['missing'])}")
