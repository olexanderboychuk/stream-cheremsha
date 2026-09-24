import ast
with open('/home/oleksandrboichuk/Dev/Self/stream-cheremsha/src/stream_cheremsha/overlays/battle_overlay.py') as f:
    content = f.read()
try:
    ast.parse(content)
    print('PARSE OK')
except SyntaxError as e:
    print(f'PARSE ERROR at line {e.lineno}: {e.msg}')
