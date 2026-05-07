from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


def _expect_dict(v: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(v, dict):
        raise ValueError(f"{path} must be an object")
    return v


def _expect_str(v: Any, *, path: str) -> str:
    if not isinstance(v, str):
        raise ValueError(f"{path} must be a string")
    s = v.strip()
    if not s:
        raise ValueError(f"{path} must be non-empty")
    return s


def _expect_int(v: Any, *, path: str) -> int:
    if not isinstance(v, int) or isinstance(v, bool):
        raise ValueError(f"{path} must be an integer")
    return v


def _expect_sha256_hex(v: Any, *, path: str) -> str:
    s = _expect_str(v, path=path)
    if len(s) != 64:
        raise ValueError(f"{path} must be 64 hex chars")
    lower = s.lower()
    if any(c not in "0123456789abcdef" for c in lower):
        raise ValueError(f"{path} must be hex")
    return lower


def _expect_https_url(v: Any, *, path: str) -> str:
    s = _expect_str(v, path=path)
    if not (s.startswith("https://") or s.startswith("http://")):
        raise ValueError(f"{path} must be http(s) URL")
    return s


@dataclass(frozen=True, slots=True)
class FileAsset:
    url: str
    sha256: str

    @staticmethod
    def from_obj(obj: Any, *, path: str) -> FileAsset:
        d = _expect_dict(obj, path=path)
        url = _expect_https_url(d.get("url"), path=f"{path}.url")
        sha256 = _expect_sha256_hex(d.get("sha256"), path=f"{path}.sha256")
        return FileAsset(url=url, sha256=sha256)


@dataclass(frozen=True, slots=True)
class WindowsPlatform:
    installer: FileAsset
    portable_zip: FileAsset | None

    @staticmethod
    def from_obj(obj: Any, *, path: str) -> WindowsPlatform:
        d = _expect_dict(obj, path=path)
        installer = FileAsset.from_obj(d.get("installer"), path=f"{path}.installer")
        portable_zip_obj = d.get("portable_zip")
        portable_zip = (
            None
            if portable_zip_obj is None
            else FileAsset.from_obj(portable_zip_obj, path=f"{path}.portable_zip")
        )
        return WindowsPlatform(installer=installer, portable_zip=portable_zip)


@dataclass(frozen=True, slots=True)
class LinuxPlatform:
    releases_url: str

    @staticmethod
    def from_obj(obj: Any, *, path: str) -> LinuxPlatform:
        d = _expect_dict(obj, path=path)
        releases_url = _expect_https_url(
            d.get("releases_url"),
            path=f"{path}.releases_url",
        )
        return LinuxPlatform(releases_url=releases_url)


@dataclass(frozen=True, slots=True)
class Platforms:
    windows: WindowsPlatform | None
    linux: LinuxPlatform | None

    @staticmethod
    def from_obj(obj: Any, *, path: str) -> Platforms:
        d = _expect_dict(obj, path=path)
        win_obj = d.get("windows")
        lin_obj = d.get("linux")
        windows = (
            None
            if win_obj is None
            else WindowsPlatform.from_obj(win_obj, path=f"{path}.windows")
        )
        linux = None if lin_obj is None else LinuxPlatform.from_obj(lin_obj, path=f"{path}.linux")
        if windows is None and linux is None:
            raise ValueError(f"{path} must contain at least one platform")
        return Platforms(windows=windows, linux=linux)


@dataclass(frozen=True, slots=True)
class LatestManifest:
    schema: int
    version: str
    tag: str
    published_at: str
    platforms: Platforms
    changelog_url: str

    @staticmethod
    def from_json(raw: str) -> LatestManifest:
        try:
            parsed: Any = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError("latest.json is invalid JSON") from e

        obj = _expect_dict(parsed, path="$")

        schema = _expect_int(obj.get("schema"), path="schema")
        if schema != 1:
            raise ValueError(f"Unsupported manifest schema: {schema}")

        version = _expect_str(obj.get("version"), path="version")
        tag = _expect_str(obj.get("tag"), path="tag")
        published_at = _expect_str(obj.get("published_at"), path="published_at")
        platforms = Platforms.from_obj(obj.get("platforms"), path="platforms")
        changelog_url = _expect_https_url(obj.get("changelog_url"), path="changelog_url")

        return LatestManifest(
            schema=schema,
            version=version,
            tag=tag,
            published_at=published_at,
            platforms=platforms,
            changelog_url=changelog_url,
        )
