from __future__ import annotations

import sys
from pathlib import Path

import pytest

from stream_cheremsha.actions.actions_launch_program import (
    split_command_line_arguments,
    validate_program_path,
)


def test_split_command_line_arguments_empty() -> None:
    assert split_command_line_arguments("") == []
    assert split_command_line_arguments("   ") == []


def test_split_command_line_arguments_simple_tokens() -> None:
    assert split_command_line_arguments("one two") == ["one", "two"]
    assert split_command_line_arguments("--mode fast") == ["--mode", "fast"]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX executable bit")
def test_validate_program_path_requires_executable_bit(tmp_path: Path) -> None:
    p = tmp_path / "tool"
    p.write_bytes(b"\x7fELF")  # not a valid ELF, only testing chmod / access
    p.chmod(0o644)
    with pytest.raises(PermissionError):
        validate_program_path(str(p))
    p.chmod(0o755)
    out = validate_program_path(str(p))
    assert out.name == "tool"
