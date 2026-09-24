with open('/home/oleksandrboichuk/Dev/Self/stream-cheremsha/src/stream_cheremsha/overlays/battle_overlay.py') as f:
    lines = f.readlines()
print(f'total lines: {len(lines)}')
for i, l in enumerate(lines):
    if '"""' in l:
        print(f'line {i+1}: {repr(l[:80])}')
