from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="Git tag, e.g. v0.1.9")
    ap.add_argument(
        "--repo",
        required=True,
        help="owner/repo, e.g. olexanderboychuk/stream-cheremsha",
    )
    ap.add_argument("--installer-path", required=True)
    ap.add_argument("--portable-zip-path", required=True)
    ap.add_argument(
        "--appimage-path",
        default=None,
        help="Optional Linux AppImage artifact for platforms.linux.appimage",
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    tag = str(args.tag).strip()
    if not tag.startswith("v"):
        raise SystemExit("tag must start with 'v' (e.g. v0.1.9)")
    version = tag[1:]
    repo = str(args.repo).strip()

    installer_path = Path(args.installer_path)
    portable_zip_path = Path(args.portable_zip_path)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not installer_path.is_file():
        raise SystemExit(f"installer not found: {installer_path}")
    if not portable_zip_path.is_file():
        raise SystemExit(f"portable zip not found: {portable_zip_path}")

    installer_name = installer_path.name
    portable_zip_name = portable_zip_path.name

    base = f"https://github.com/{repo}/releases/download/{tag}"

    linux_platform: dict[str, object] = {
        "releases_url": f"https://github.com/{repo}/releases/tag/{tag}",
    }
    if args.appimage_path:
        appimage_path = Path(args.appimage_path)
        if not appimage_path.is_file():
            raise SystemExit(f"appimage not found: {appimage_path}")
        linux_platform["appimage"] = {
            "url": f"{base}/{appimage_path.name}",
            "sha256": _sha256_file(appimage_path),
        }

    manifest = {
        "schema": 1,
        "version": version,
        "tag": tag,
        "published_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "platforms": {
            "windows": {
                "installer": {
                    "url": f"{base}/{installer_name}",
                    "sha256": _sha256_file(installer_path),
                },
                "portable_zip": {
                    "url": f"{base}/{portable_zip_name}",
                    "sha256": _sha256_file(portable_zip_path),
                },
            },
            "linux": linux_platform,
        },
        "changelog_url": f"https://github.com/{repo}/blob/{tag}/CHANGELOG.md",
    }

    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
