with open('/home/oleksandrboichuk/Dev/Self/stream-cheremsha/src/stream_cheremsha/overlays/battle_overlay.py') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if 'f"""' in l:
        print(f'f-string starts at line {i+1}')
        # Find closing
        for j in range(i, len(lines)):
            if lines[j].strip() == '"""' or lines[j].strip().startswith('"""'):
                print(f'closing at line {j+1}: {repr(lines[j])}')
                break
