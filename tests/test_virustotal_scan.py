from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_VT_PATH = _ROOT / "scripts" / "ci" / "virustotal_scan.py"


def _load_virustotal_scan():
    spec = importlib.util.spec_from_file_location("virustotal_scan", _VT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {_VT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["virustotal_scan"] = module
    spec.loader.exec_module(module)
    return module


vt = _load_virustotal_scan()


def test_parse_results_collects_malicious_and_suspicious() -> None:
    attributes = {
        "stats": {"malicious": 1, "suspicious": 1, "undetected": 70},
        "results": {
            "AhnLab-V3": {"category": "malicious", "result": "Trojan/Win32.Agent"},
            "Avast": {"category": "undetected", "result": None},
            "GData": {"category": "suspicious", "result": "Gen:Variant.Application"},
        },
    }
    result = vt._parse_results(
        Path("Cheremsha-Setup-v1.exe"),
        "analysis-1",
        "abc123",
        attributes,
    )
    assert result.malicious == 1
    assert result.suspicious == 1
    assert len(result.detections) == 2
    assert result.permalink.endswith("/abc123")


def test_render_markdown_clean_status() -> None:
    results = [
        vt.FileScanResult(
            path=Path("setup.exe"),
            analysis_id="a1",
            sha256="deadbeef",
            stats={"malicious": 0, "suspicious": 0, "undetected": 72},
            detections=[],
        )
    ]
    md = vt.render_markdown(results, "v1.0.0")
    assert "**Status: CLEAN**" in md
    assert "setup.exe" in md


def test_to_json_dict_shape() -> None:
    results = [
        vt.FileScanResult(
            path=Path("setup.exe"),
            analysis_id="a1",
            sha256="deadbeef",
            stats={"malicious": 1, "undetected": 71},
            detections=[vt.EngineResult("Avast", "malicious", "Win32:Malware")],
        )
    ]
    payload = vt.to_json_dict(results, "v1.0.0")
    assert payload["schema"] == 1
    assert payload["tag"] == "v1.0.0"
    assert payload["files"][0]["detections"][0]["engine"] == "Avast"


def test_main_fails_on_malicious(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = tmp_path / "setup.exe"
    artifact.write_bytes(b"fake-exe")
    monkeypatch.setenv("VIRUSTOTAL_API_KEY", "test-key")

    malicious = vt.FileScanResult(
        path=artifact,
        analysis_id="a1",
        sha256="abc",
        stats={"malicious": 2, "undetected": 70},
        detections=[],
    )
    with patch.object(vt, "scan_file", return_value=malicious):
        with patch.object(vt, "httpx"):
            with pytest.raises(SystemExit) as exc:
                vt.main(["--tag", "v1.0.0", "--out-dir", str(tmp_path), str(artifact)])
    assert exc.value.code == 1


def test_upload_file_small_uses_files_endpoint(tmp_path: Path) -> None:
    artifact = tmp_path / "small.exe"
    artifact.write_bytes(b"tiny")
    client = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"data": {"id": "analysis-small"}}
    client.post.return_value = response

    analysis_id = vt._upload_file(client, "key", artifact)
    assert analysis_id == "analysis-small"
    client.post.assert_called_once()
    assert client.post.call_args.args[0].endswith("/files")


def test_upload_file_large_uses_upload_url(tmp_path: Path) -> None:
    artifact = tmp_path / "large.exe"
    artifact.write_bytes(b"x" * (33 * 1024 * 1024))
    client = MagicMock()
    url_response = MagicMock()
    url_response.json.return_value = {"data": "https://upload.example/vt"}
    upload_response = MagicMock()
    upload_response.status_code = 200
    upload_response.json.return_value = {"data": {"id": "analysis-large"}}
    client.get.return_value = url_response
    client.post.return_value = upload_response

    analysis_id = vt._upload_file(client, "key", artifact)
    assert analysis_id == "analysis-large"
    client.get.assert_called_once()
    client.post.assert_called_once()
    assert client.post.call_args.args[0] == "https://upload.example/vt"


def test_wait_for_analysis_polls_until_completed() -> None:
    client = MagicMock()
    pending = MagicMock()
    pending.status_code = 200
    pending.json.return_value = {"data": {"attributes": {"status": "queued"}}}
    completed = MagicMock()
    completed.status_code = 200
    completed.json.return_value = {
        "data": {
            "attributes": {
                "status": "completed",
                "stats": {"malicious": 0, "undetected": 72},
                "results": {},
            }
        }
    }
    client.get.side_effect = [pending, completed]

    with patch.object(vt.time, "sleep"):
        attributes = vt._wait_for_analysis(client, "key", "analysis-1")

    assert attributes["status"] == "completed"
    assert client.get.call_count == 2


def test_main_writes_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = tmp_path / "setup.exe"
    artifact.write_bytes(b"fake-exe")
    monkeypatch.setenv("VIRUSTOTAL_API_KEY", "test-key")

    clean = vt.FileScanResult(
        path=artifact,
        analysis_id="a1",
        sha256="abc",
        stats={"malicious": 0, "undetected": 72},
        detections=[],
    )
    with patch.object(vt, "scan_file", return_value=clean):
        with patch.object(vt, "httpx"):
            vt.main(["--tag", "v1.0.0", "--out-dir", str(tmp_path), str(artifact)])

    json_path = tmp_path / "virustotal-report.json"
    md_path = tmp_path / "virustotal-report.md"
    assert json_path.is_file()
    assert md_path.is_file()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["tag"] == "v1.0.0"
