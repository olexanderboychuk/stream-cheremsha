from __future__ import annotations

import argparse
import re
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2]


def _read_pyproject_version(pyproject_path: Path) -> str:
    import tomllib

    raw = pyproject_path.read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    try:
        version = data["project"]["version"]
    except KeyError as e:
        raise SystemExit(f"Missing [project].version in {pyproject_path}") from e
    if not isinstance(version, str) or not version:
        raise SystemExit(f"Invalid [project].version in {pyproject_path}: {version!r}")
    return version


def _read_init_version(init_path: Path) -> str:
    text = init_path.read_text(encoding="utf-8")
    m = re.search(r'^\s*__version__\s*=\s*"([^"]+)"\s*$', text, flags=re.MULTILINE)
    if not m:
        raise SystemExit(f'Could not find __version__ = "..." in {init_path}')
    return m.group(1)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Validate that repo version matches release tag.")
    p.add_argument("--tag-version", required=True, help='Version without "v" prefix, e.g. 1.2.3')
    ns = p.parse_args(argv)

    tag_version = ns.tag_version.strip()
    if not tag_version:
        raise SystemExit("Empty --tag-version")

    pyproject_path = _ROOT / "pyproject.toml"
    init_path = _ROOT / "src" / "stream_cheremsha" / "__init__.py"

    pyproject_version = _read_pyproject_version(pyproject_path)
    init_version = _read_init_version(init_path)

    problems: list[str] = []
    if pyproject_version != tag_version:
        problems.append(
            f"pyproject.toml [project].version={pyproject_version!r} does not match tag {tag_version!r}",
        )
    if init_version != tag_version:
        problems.append(
            f"src/stream_cheremsha/__init__.py __version__={init_version!r} does not match tag {tag_version!r}",
        )

    if problems:
        joined = "\n".join(f"- {p}" for p in problems)
        raise SystemExit(f"Release version mismatch:\n{joined}")


if __name__ == "__main__":
    main()
