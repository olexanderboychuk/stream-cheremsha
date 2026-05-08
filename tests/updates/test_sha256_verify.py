from pathlib import Path

from stream_cheremsha.updates.downloader import sha256_file


def test_sha256_file_matches_known_value(tmp_path: Path) -> None:
    p = tmp_path / "x.bin"
    p.write_bytes(b"abc")
    assert sha256_file(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
