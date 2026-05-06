from __future__ import annotations

from dataclasses import dataclass

from stream_cheremsha.activity.models import ActivityItem, now_hms


@dataclass(slots=True)
class _Bucket:
    kind: str
    user: str
    count: int
    start_mono: float


class LikeShareAggregator:
    """Coalesce high-volume like/share events into time-windowed rows."""

    def __init__(self, *, window_sec: float = 7.0) -> None:
        self._window = max(1.0, float(window_sec))
        self._buckets: dict[tuple[str, str], _Bucket] = {}

    def ingest(self, *, kind: str, user: str, n: int, now_mono: float) -> None:
        kk = (str(kind), str(user or ""))
        inc = max(1, int(n))
        b = self._buckets.get(kk)
        if b is None:
            self._buckets[kk] = _Bucket(
                kind=kk[0],
                user=kk[1],
                count=inc,
                start_mono=float(now_mono),
            )
            return
        b.count += inc

    def flush_ready(self, *, now_mono: float) -> list[ActivityItem]:
        out: list[ActivityItem] = []
        t = float(now_mono)
        done: list[tuple[str, str]] = []
        for k, b in self._buckets.items():
            if (t - b.start_mono) < self._window:
                continue
            done.append(k)
            # v1: user may be empty when the platform doesn't provide it.
            out.append(
                ActivityItem(
                    platform="tiktok",
                    kind=b.kind,  # type: ignore[arg-type]
                    user=b.user,
                    detail="",
                    count=b.count,
                    icon_url="",
                    time_hms=now_hms(),
                ),
            )
        for k in done:
            self._buckets.pop(k, None)
        return out

