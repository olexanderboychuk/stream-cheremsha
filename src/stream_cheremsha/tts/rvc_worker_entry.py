"""RVC worker process (``multiprocessing`` ``spawn``) — heavy torch/fairseq live here only.

When the parent terminates this process, the OS reclaims all RSS used by the model
(unlike in-process unload, which often leaves the parent at a high watermark).
"""

from __future__ import annotations

import logging
import tempfile
import traceback
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_work_tmp_dir: str | None = None


def rvc_worker_main(conn: Any) -> None:
    """Handle ``("load", ...)``, ``("infer", wav_bytes)``, ``("shutdown",)`` over *conn*."""
    global _work_tmp_dir
    infer: Any = None
    try:
        while True:
            try:
                msg = conn.recv()
            except EOFError:
                break
            if not isinstance(msg, tuple) or not msg:
                break
            tag = msg[0]
            if tag == "shutdown":
                break
            if tag == "load":
                (
                    _,
                    models_dir,
                    model_path,
                    index_path,
                    use_cuda,
                    tmp_base,
                ) = msg
                _work_tmp_dir = tmp_base if tmp_base else None
                try:
                    from stream_cheremsha.tts.rvc_wav import (
                        _patch_torch_load_for_fairseq_checkpoints,
                    )

                    _patch_torch_load_for_fairseq_checkpoints()
                    from rvc_python.infer import RVCInference  # noqa: PLC0415

                    device = "cuda:0" if use_cuda else "cpu:0"
                    infer = RVCInference(
                        models_dir=models_dir,
                        device=device,
                        model_path=model_path,
                        index_path=index_path or "",
                        version="v2",
                    )
                    conn.send(("ok", None))
                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error("RVC worker load failed: %s\n%s", e, tb)
                    try:
                        conn.send(("err", f"{type(e).__name__}: {e}"))
                    except (BrokenPipeError, EOFError, OSError):
                        pass
                    return
            elif tag == "infer":
                if infer is None:
                    conn.send(("err", "RVC worker: not loaded"))
                    continue
                _, wav_bytes = msg
                try:
                    with tempfile.TemporaryDirectory(
                        prefix="cheremsha_rvc_",
                        dir=_work_tmp_dir,
                    ) as td:
                        tdir = Path(td)
                        pin = tdir / "in.wav"
                        pout = tdir / "out.wav"
                        pin.write_bytes(wav_bytes)
                        infer.infer_file(str(pin), str(pout))
                        out = pout.read_bytes()
                    conn.send(("ok", out))
                except Exception as e:
                    try:
                        conn.send(("err", f"{type(e).__name__}: {e}"))
                    except (BrokenPipeError, EOFError, OSError):
                        pass
            else:
                try:
                    conn.send(("err", f"unknown message {tag!r}"))
                except (BrokenPipeError, EOFError, OSError):
                    pass
    finally:
        try:
            conn.close()
        except OSError:
            pass
