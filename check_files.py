import json
from pathlib import Path

data = json.load(open('dataset/raw/train1.json', encoding='utf-8'))
annotated_dir = Path('dataset/annotated')

found_count = 0
missing_count = 0

print('Проверка поиска файлов:')
for i, entry in enumerate(data[:10]):
    fu = entry["file_upload"]
    # Extracts the actual filename (after the UUID prefix)
    actual_name = fu.split('-', 1)[-1] if '-' in fu else fu
    
    # Search for file
    src_image = annotated_dir / actual_name
    found = src_image.exists()
    
    if found:
        found_count += 1
        status = "✓ FOUND"
    else:
        missing_count += 1
        status = "✗ NOT FOUND"
        # Try case-insensitive search
        candidates = [p for p in annotated_dir.iterdir() if p.name.lower() == actual_name.lower()]
        if candidates:
            status += f" (case-insensitive found: {candidates[0].name})"
    
    print(f'{i+1}. {actual_name} -> {status}')

print(f'\nTotal in train1.json: {len(data)}')
print(f'Found: {found_count}')
print(f'Missing: {missing_count}')
