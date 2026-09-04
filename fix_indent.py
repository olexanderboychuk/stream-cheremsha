#!/usr/bin/env python3
with open("D:\\dev\\stream-cheremsha\\src\\stream_cheremsha\\ui\\main_window.py") as f:
    lines = f.readlines()

# Fix line 870 (index 869) - add 8 spaces
lines[869] = "        self._activity_engine = ActivityEngine(\n"

with open("D:\\dev\\stream-cheremsha\\src\\stream_cheremsha\\ui\\main_window.py", "w") as f:
    f.writelines(lines)
print("Fixed line 870")
