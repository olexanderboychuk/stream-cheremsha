#!/usr/bin/env python3
import sys

filepath = r"D:\dev\stream-cheremsha\src\stream_cheremsha\actions\engine.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# --- Part 1: Add activity_engine parameter to __init__ ---
old_init_start = "class PlatformActionsEngine:"
# Find the class definition and its docstring
# We'll replace from "class PlatformActionsEngine:" through the old __init__

# Let's be more surgical: replace just the __init__ signature part
# Find the old __init__ signature line
lines = content.split("\n")
# Find line with "def __init__(self,"
init_idx = None
for i, line in enumerate(lines):
    if "def __init__(self," in line and i > 555 and i < 570:
        init_idx = i
        break

if init_idx is None:
    print("ERROR: Could not find __init__ signature")
    sys.exit(1)

# Find the end of the __init__ method (next method or class)
# For now, let's just replace the specific old signature we know
old_signature = """    def __init__(
        self,
        sink: AudioSink,
        rules: list[RuleV1] | None = None,
        *,
        status_callback: StatusCallback | None = None,
        tts_speak: TtsSpeakCallback | None = None,
        pubsub: OverlayPubSub | None = None,
        actions_overlay_instance: str = "main",
        obs_execute: ObsExecute | None = None,
    ) -> None:"""

new_signature = """    def __init__(
        self,
        sink: AudioSink,
        rules: list[RuleV1] | None = None,
        *,
        status_callback: StatusCallback | None = None,
        tts_speak: TtsSpeakCallback | None = None,
        pubsub: OverlayPubSub | None = None,
        actions_overlay_instance: str = "main",
        obs_execute: ObsExecute | None = None,
        activity_engine: Any | None = None,
    ) -> None:"""

if old_signature in content:
    content = content.replace(old_signature, new_signature)
    print("Replaced __init__ signature")
else:
    print("ERROR: Could not find old __init__ signature")
    # Print surrounding lines
    for i in range(570 if init_idx is None else init_idx, min(585, len(lines))):
        print(f"  {i+1}: {lines[i]}")
    sys.exit(1)

# --- Part 2: Add set_activity_engine method after reset_tiktok_like_totals ---
old_reset = """    def reset_tiktok_like_totals(self) -> None:
        """Reset TikTok per-stream counters used by TikTok triggers."""
        self._tiktok_like_all_total = 0
        self._tiktok_like_user_totals.clear()
        self._tiktok_first_activity_seen_users.clear()"""

new_reset = """    def reset_tiktok_like_totals(self) -> None:
        """Reset TikTok per-stream counters used by TikTok triggers."""
        self._tiktok_like_all_total = 0
        self._tiktok_like_user_totals.clear()
        self._tiktok_first_activity_seen_users.clear()

    def set_activity_engine(self, activity_engine: Any | None) -> None:
        """Set the optional activity engine for score updates."""
        self._activity_engine = activity_engine"""

if old_reset in content:
    content = content.replace(old_reset, new_reset)
    print("Added set_activity_engine method")
else:
    print("ERROR: Could not find reset_tiktok_like_totals to insert after")

# --- Part 3: Add activity engine update calls in on_* methods ---
# We'll add a simple call in the tiktok_likes_received method as an example
# Look for the on_tiktok_likes_received method and add activity update

# First, let's verify the file was modified correctly
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Done modifying engine.py")