from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _require_supported_nuitka() -> None:
    try:
        import nuitka  # type: ignore[import-not-found]
    except Exception as e:
        raise SystemExit(
            "Nuitka is not installed. Install with: pip install -e \".[build]\"",
        ) from e

    v = getattr(nuitka, "__version__", "0").split(".")
    try:
        major = int(v[0])
    except ValueError:
        major = 0
    if major >= 4:
        raise SystemExit(
            "Unsupported Nuitka version detected (4.x). "
            "Please downgrade: pip install -e \".[build]\"",
        )


def _nuitka_cmd(
    *,
    out_dir: Path,
    onefile: bool,
    debug: bool,
    show_console: bool,
    jobs: str,
) -> list[str]:
    _require_supported_nuitka()

    qml_dir = _ROOT / "qml"
    assets_dir = _ROOT / "assets"
    piper_dir = _ROOT / "data" / "piper"

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--follow-imports",
        # Prevent external site-packages at runtime (can cause duplicate torch extensions).
        "--python-flag=isolated",
        "--python-flag=safe_path",
        # PyTorch compiler stack is not required for inference; can crash Nuitka optimization.
        # Exclude it from compilation to keep builds stable.
        "--nofollow-import-to=torch._dynamo",
        "--nofollow-import-to=torch._inductor",
        "--nofollow-import-to=torch._functorch",
        "--nofollow-import-to=torch._export",
        # RVC inference does not need distributed/RPC, but it can crash in standalone builds
        # with duplicate type registration (e.g. RpcBackendOptions already defined).
        "--nofollow-import-to=torch.distributed",
        # RVC stack (installed via `cheremsha-bootstrap-rvc`) is optional at runtime,
        # but for builds that want RVC we must force-include these dynamic imports.
        "--include-package=rvc_python",
        "--include-package-data=rvc_python",
        "--include-module=rvc_python.infer",
        "--include-package=fairseq",
        "--include-package-data=fairseq",
        "--include-package=torchcrepe",
        "--include-package-data=torchcrepe",
        "--include-package=pyworld",
        "--include-package-data=pyworld",
        "--include-module=parselmouth",
        "--include-package=av",
        "--include-package-data=av",
        "--include-module=soundfile",
        "--include-package=scipy",
        "--include-package-data=scipy",
        # Piper/ONNXRuntime: without this, standalone builds often fail to load providers.
        "--include-package=onnxruntime",
        "--include-package-data=onnxruntime",
        "--enable-plugin=pyside6",
        # Needed for QQuickWidget/QML and QMediaPlayer backends in standalone builds.
        "--include-qt-plugins=qml,multimedia",
        "--module-parameter=torch-disable-jit=yes",
        f"--output-dir={out_dir}",
        "--assume-yes-for-downloads",
        f"--include-data-dir={qml_dir}=stream_cheremsha/qml",
        f"--include-data-dir={assets_dir}=stream_cheremsha/assets",
        f"--include-data-dir={piper_dir}=stream_cheremsha/data/piper",
    ]
    if jobs:
        cmd.append(f"--jobs={jobs}")
    if onefile:
        cmd.append("--onefile")
    if debug:
        cmd.append("--debug")
    if sys.platform.startswith("win"):
        # Our app is GUI-first; show a console only when requested (helps debugging).
        if not show_console:
            cmd.append("--windows-console-mode=disable")
        cmd.append("--windows-uac-admin=false")
    else:
        # On non-Windows, console mode is the default; do not pass deprecated flags.
        # `--console` is kept for parity with Windows (no-op here).
        pass

    # Entry point (same as `cheremsha`)
    cmd.append(str((_ROOT / "app" / "main.py").resolve()))
    return cmd


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        prog="cheremsha-build",
        description="Build standalone binary via Nuitka.",
    )
    p.add_argument(
        "--out",
        default="dist/nuitka",
        help="Output directory (default: dist/nuitka)",
    )
    p.add_argument(
        "--onefile",
        action="store_true",
        help="Build a single-file executable (slower start).",
    )
    p.add_argument(
        "--fast",
        action="store_true",
        help="Fast build (default): no debug, no onefile.",
    )
    p.add_argument("--debug", action="store_true", help="Enable Nuitka debug build (slower).")
    p.add_argument(
        "--jobs",
        default=str(os.cpu_count() or 4),
        help="Nuitka jobs (integer). Default: CPU count.",
    )
    p.add_argument(
        "--console",
        action="store_true",
        help="Show a console window / console output (useful for debugging).",
    )
    ns = p.parse_args(argv)

    if ns.fast:
        ns.debug = False
        ns.onefile = False

    out = Path(ns.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cmd = _nuitka_cmd(
        out_dir=out,
        onefile=ns.onefile,
        debug=ns.debug,
        show_console=ns.console,
        jobs=str(ns.jobs),
    )
    _run(cmd)


if __name__ == "__main__":
    main()

