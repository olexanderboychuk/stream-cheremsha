from __future__ import annotations

from pathlib import Path

import pytest

from stream_cheremsha.updates import downloader
from stream_cheremsha.updates.launcher import build_updater_args


class _Response:
    headers = {"Content-Length": "6"}

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self):
        yield b"abc"
        yield b"def"


def test_download_reports_real_bytes_and_replaces_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(downloader.httpx, "stream", lambda *args, **kwargs: _Response())
    monkeypatch.setattr(downloader, "MIN_DOWNLOAD_SIZE_BYTES", 1)
    destination = tmp_path / "installer.exe"
    updates: list[tuple[int, int | None]] = []

    downloader.download_file(
        "https://example.test/update.exe",
        destination,
        progress=lambda downloaded, total: updates.append((downloaded, total)),
    )

    assert destination.read_bytes() == b"abcdef"
    assert updates == [(0, 6), (3, 6), (6, 6)]
    assert not (tmp_path / "installer.exe.part").exists()


def test_cancelled_download_removes_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(downloader.httpx, "stream", lambda *args, **kwargs: _Response())
    destination = tmp_path / "installer.exe"

    with pytest.raises(downloader.DownloadCancelled):
        downloader.download_file(
            "https://example.test/update.exe",
            destination,
            cancelled=lambda: True,
        )

    assert not destination.exists()
    assert not (tmp_path / "installer.exe.part").exists()


def test_updater_arguments_preserve_spaces_and_unicode_paths() -> None:
    install_dir = Path("C:/Program Files/Черемша")
    app = install_dir / "cheremsha.exe"

    args = build_updater_args(
        url="https://example.test/Cheremsha Setup.exe",
        sha256="a" * 64,
        version="1.4.2",
        install_dir=install_dir,
        app=app,
        parent_pid=123,
        locale="uk",
    )

    assert args[args.index("--install-dir") + 1] == str(install_dir)
    assert args[args.index("--app") + 1] == str(app)
    assert args[args.index("--url") + 1].endswith("Cheremsha Setup.exe")
