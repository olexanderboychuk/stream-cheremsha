from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

VT_API_BASE = "https://www.virustotal.com/api/v3"
SMALL_FILE_LIMIT = 32 * 1024 * 1024
POLL_INTERVAL_SEC = 20
POLL_TIMEOUT_SEC = 30 * 60
RATE_LIMIT_PAUSE_SEC = 16


@dataclass(frozen=True)
class EngineResult:
    engine: str
    category: str
    result: str | None


@dataclass
class FileScanResult:
    path: Path
    analysis_id: str
    sha256: str
    stats: dict[str, int]
    detections: list[EngineResult]

    @property
    def malicious(self) -> int:
        return int(self.stats.get("malicious", 0))

    @property
    def suspicious(self) -> int:
        return int(self.stats.get("suspicious", 0))

    @property
    def permalink(self) -> str:
        return f"https://www.virustotal.com/gui/file/{self.sha256}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _api_key() -> str:
    key = os.environ.get("VIRUSTOTAL_API_KEY", "").strip()
    if not key:
        raise SystemExit("VIRUSTOTAL_API_KEY environment variable is not set")
    return key


def _headers(api_key: str) -> dict[str, str]:
    return {"x-apikey": api_key, "accept": "application/json"}


def _upload_file(client: httpx.Client, api_key: str, file_path: Path) -> str:
    headers = _headers(api_key)
    upload_timeout = httpx.Timeout(600.0, connect=30.0)
    file_size = file_path.stat().st_size

    if file_size <= SMALL_FILE_LIMIT:
        with file_path.open("rb") as handle:
            response = client.post(
                f"{VT_API_BASE}/files",
                headers=headers,
                files={"file": (file_path.name, handle)},
                timeout=upload_timeout,
            )
    else:
        response = client.get(
            f"{VT_API_BASE}/files/upload_url",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        upload_url = response.json()["data"]
        with file_path.open("rb") as handle:
            response = client.post(
                upload_url,
                files={"file": (file_path.name, handle)},
                timeout=upload_timeout,
            )

    if response.status_code == 429:
        raise SystemExit(f"VirusTotal rate limit exceeded while uploading {file_path.name}")
    response.raise_for_status()
    return response.json()["data"]["id"]


def _wait_for_analysis(client: httpx.Client, api_key: str, analysis_id: str) -> dict:
    headers = _headers(api_key)
    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    while time.monotonic() < deadline:
        response = client.get(
            f"{VT_API_BASE}/analyses/{analysis_id}",
            headers=headers,
            timeout=30.0,
        )
        if response.status_code == 429:
            time.sleep(POLL_INTERVAL_SEC)
            continue
        response.raise_for_status()
        attributes = response.json()["data"]["attributes"]
        status = attributes.get("status")
        if status == "completed":
            return attributes
        if status == "failed":
            raise SystemExit(f"VirusTotal analysis failed: {analysis_id}")
        time.sleep(POLL_INTERVAL_SEC)
    raise SystemExit(f"VirusTotal analysis timed out after {POLL_TIMEOUT_SEC}s: {analysis_id}")


def _parse_results(
    path: Path,
    analysis_id: str,
    sha256: str,
    attributes: dict,
) -> FileScanResult:
    stats = {key: int(value) for key, value in attributes.get("stats", {}).items()}
    results = attributes.get("results") or {}
    detections: list[EngineResult] = []
    for engine, info in sorted(results.items()):
        category = str(info.get("category", ""))
        if category in ("malicious", "suspicious"):
            detections.append(
                EngineResult(
                    engine=engine,
                    category=category,
                    result=info.get("result"),
                )
            )
    return FileScanResult(
        path=path,
        analysis_id=analysis_id,
        sha256=sha256,
        stats=stats,
        detections=detections,
    )


def scan_file(client: httpx.Client, api_key: str, file_path: Path) -> FileScanResult:
    if not file_path.is_file():
        raise SystemExit(f"File not found: {file_path}")
    sha256 = _sha256_file(file_path)
    print(
        f"Uploading {file_path.name} ({file_path.stat().st_size} bytes, sha256={sha256}) "
        "to VirusTotal..."
    )
    analysis_id = _upload_file(client, api_key, file_path)
    print(f"  analysis id: {analysis_id}, waiting for results...")
    attributes = _wait_for_analysis(client, api_key, analysis_id)
    result = _parse_results(file_path, analysis_id, sha256, attributes)
    print(
        f"  done: malicious={result.malicious} suspicious={result.suspicious} "
        f"undetected={result.stats.get('undetected', 0)}"
    )
    return result


def render_markdown(results: list[FileScanResult], tag: str) -> str:
    lines = [
        f"# VirusTotal scan report — Cheremsha {tag}",
        "",
        "Multi-engine scan via [VirusTotal](https://www.virustotal.com/).",
        "",
    ]
    if any(result.malicious > 0 for result in results):
        lines.append("**Status: FAILED** — at least one engine reported malicious.")
    elif any(result.suspicious > 0 for result in results):
        lines.append("**Status: WARNING** — suspicious detections reported.")
    else:
        lines.append("**Status: CLEAN** — no malicious or suspicious detections.")
    lines.append("")

    for result in results:
        lines.extend(
            [
                f"## `{result.path.name}`",
                "",
                f"- SHA-256: `{result.sha256}`",
                f"- Permalink: {result.permalink}",
                f"- Analysis id: `{result.analysis_id}`",
                "",
                "| Stat | Count |",
                "|------|------:|",
            ]
        )
        for key in sorted(result.stats):
            lines.append(f"| {key} | {result.stats[key]} |")
        lines.append("")
        if result.detections:
            lines.extend(
                [
                    "### Detections",
                    "",
                    "| Engine | Category | Result |",
                    "|--------|----------|--------|",
                ]
            )
            for detection in result.detections:
                lines.append(
                    f"| {detection.engine} | {detection.category} | {detection.result or ''} |"
                )
            lines.append("")
        else:
            lines.extend(["_No malicious or suspicious engine results._", ""])

    return "\n".join(lines).rstrip() + "\n"


def to_json_dict(results: list[FileScanResult], tag: str) -> dict:
    return {
        "schema": 1,
        "tag": tag,
        "files": [
            {
                "name": result.path.name,
                "sha256": result.sha256,
                "analysis_id": result.analysis_id,
                "permalink": result.permalink,
                "stats": result.stats,
                "detections": [
                    {
                        "engine": detection.engine,
                        "category": detection.category,
                        "result": detection.result,
                    }
                    for detection in result.detections
                ],
            }
            for result in results
        ],
    }


def _exit_if_failed(results: list[FileScanResult], *, fail_on_suspicious: bool) -> None:
    for result in results:
        if result.malicious > 0:
            print(
                f"ERROR: {result.path.name} has {result.malicious} malicious detection(s).",
                file=sys.stderr,
            )
            raise SystemExit(1)
        if fail_on_suspicious and result.suspicious > 0:
            print(
                f"ERROR: {result.path.name} has {result.suspicious} suspicious detection(s).",
                file=sys.stderr,
            )
            raise SystemExit(1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Scan release artifacts with VirusTotal API v3.")
    parser.add_argument("--tag", required=True, help="Release tag, e.g. v0.10.0")
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory for virustotal-report.json and .md",
    )
    parser.add_argument(
        "--fail-on-suspicious",
        action="store_true",
        help="Also fail when any engine reports suspicious (default: fail only on malicious)",
    )
    parser.add_argument("files", nargs="+", help="Artifact paths to scan")
    args = parser.parse_args(argv)

    api_key = _api_key()
    paths = [Path(path) for path in args.files]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[FileScanResult] = []
    with httpx.Client() as client:
        for index, path in enumerate(paths):
            if index > 0:
                time.sleep(RATE_LIMIT_PAUSE_SEC)
            results.append(scan_file(client, api_key, path.resolve()))

    json_path = out_dir / "virustotal-report.json"
    md_path = out_dir / "virustotal-report.md"
    json_path.write_text(
        json.dumps(to_json_dict(results, args.tag), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(results, args.tag), encoding="utf-8")
    print(f"Wrote {json_path} and {md_path}")

    _exit_if_failed(results, fail_on_suspicious=args.fail_on_suspicious)


if __name__ == "__main__":
    main()
