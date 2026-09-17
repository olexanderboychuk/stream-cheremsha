"""Per-instance overlay controller groups.

Singleton controllers publish to ``overlay:{type}:main`` and load the type
singleton config, so user widget instances either starve (no fan-out) or get
stomped by singleton state. An :class:`InstanceControllerGroup` owns one
controller per widget *instance* of a type: each loads its own merged
instance settings and publishes to its own topic. Chat/stream events are
dispatched to every member; per-instance state (rankings, rotation timeline)
stays isolated.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

_LOG = logging.getLogger(__name__)


def instance_config_loader(
    type_id: str,
    instance_id: str,
    parser: Callable[[str], Any],
    fallback_loader: Callable[[], Any],
) -> Callable[[], Any]:
    """Build a config loader bound to one widget instance.

    Returns ``parser(merged_settings)`` for the instance, falling back to the
    type defaults loader when the instance is missing, mistyped, or invalid.
    Never raises.
    """

    def _load() -> Any:
        try:
            from stream_cheremsha.overlays.widget_instances import get_instance, merged_settings

            inst = get_instance(str(instance_id or ""))
            if inst is not None and inst.type_id == type_id:
                return parser(json.dumps(merged_settings(inst), ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001 - loader must never break publishing
            _LOG.warning("instance config load failed for %s/%s: %s", type_id, instance_id, exc)
        return fallback_loader()

    return _load


class InstanceControllerGroup:
    """Owns one controller per widget instance of a single overlay type.

    ``factory`` is ``(instance_id) -> controller``. Controllers are reused
    across :meth:`sync_instances` so ranking/session state survives unrelated
    changes; removed instances are stopped and dropped.
    """

    def __init__(
        self,
        type_id: str,
        factory: Callable[[str], Any],
    ) -> None:
        self._type_id = str(type_id)
        self._factory = factory
        self._members: dict[str, Any] = {}
        self._pubsub: Any | None = None
        self._loop: Any | None = None

    @property
    def type_id(self) -> str:
        return self._type_id

    def instance_ids(self) -> list[str]:
        return sorted(self._members.keys())

    def sync_instances(self, *, start: bool = True) -> None:
        """Reconcile members with the widget instance store."""
        from stream_cheremsha.overlays.widget_instances import list_instances

        try:
            wanted = {x.id for x in list_instances() if x.type_id == self._type_id}
        except Exception as exc:  # noqa: BLE001 - never break the caller
            _LOG.warning("instance sync failed for %s: %s", self._type_id, exc)
            return
        for iid in sorted(wanted - set(self._members)):
            try:
                ctl = self._factory(iid)
            except Exception as exc:  # noqa: BLE001 - one bad instance must not block others
                _LOG.warning("controller create failed for %s/%s: %s", self._type_id, iid, exc)
                continue
            if self._pubsub is not None:
                setter = getattr(ctl, "set_pubsub", None)
                if callable(setter):
                    setter(self._pubsub)
            if self._loop is not None:
                setter = getattr(ctl, "set_event_loop", None)
                if callable(setter):
                    setter(self._loop)
            if start:
                starter = getattr(ctl, "start", None)
                if callable(starter):
                    try:
                        starter()
                    except Exception as exc:  # noqa: BLE001
                        _LOG.warning(
                            "controller start failed for %s/%s: %s", self._type_id, iid, exc
                        )
            self._members[iid] = ctl
        for iid in sorted(set(self._members) - wanted):
            ctl = self._members.pop(iid)
            stopper = getattr(ctl, "stop", None)
            if callable(stopper):
                try:
                    stopper()
                except Exception:  # noqa: BLE001 - best effort teardown
                    pass

    def reload_instance(self, instance_id: str) -> bool:
        """Reload a single member's config (e.g. after its settings were saved)."""
        ctl = self._members.get(str(instance_id or ""))
        if ctl is None:
            return False
        reloader = getattr(ctl, "reload_config", None)
        if not callable(reloader):
            return False
        try:
            reloader()
        except Exception as exc:  # noqa: BLE001
            _LOG.warning(
                "controller reload failed for %s/%s: %s", self._type_id, instance_id, exc
            )
            return False
        return True

    def reload_config(self) -> None:
        for ctl in list(self._members.values()):
            reloader = getattr(ctl, "reload_config", None)
            if callable(reloader):
                try:
                    reloader()
                except Exception:  # noqa: BLE001 - best effort
                    pass

    def initial_state(self) -> dict[str, Any]:
        for ctl in self._members.values():
            getter = getattr(ctl, "initial_state", None)
            if callable(getter):
                try:
                    state = getter()
                except Exception:  # noqa: BLE001
                    continue
                if isinstance(state, dict):
                    return state
        return {}

    def set_pubsub(self, pubsub: Any | None) -> None:
        self._pubsub = pubsub
        for ctl in self._members.values():
            setter = getattr(ctl, "set_pubsub", None)
            if callable(setter):
                setter(pubsub)

    def set_event_loop(self, loop: Any | None) -> None:
        self._loop = loop
        for ctl in self._members.values():
            setter = getattr(ctl, "set_event_loop", None)
            if callable(setter):
                setter(loop)

    def start(self) -> None:
        for ctl in list(self._members.values()):
            starter = getattr(ctl, "start", None)
            if callable(starter):
                try:
                    starter()
                except Exception:  # noqa: BLE001 - best effort
                    pass

    def stop(self) -> None:
        for ctl in list(self._members.values()):
            stopper = getattr(ctl, "stop", None)
            if callable(stopper):
                try:
                    stopper()
                except Exception:  # noqa: BLE001 - best effort
                    pass

    # -- event fan-out: one method per controller event used by callers --------

    def _each(self, name: str, *args: Any, **kwargs: Any) -> None:
        for ctl in list(self._members.values()):
            fn = getattr(ctl, name, None)
            if not callable(fn):
                continue
            try:
                fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - one bad member must not block others
                _LOG.warning(
                    "controller event %s failed for %s: %s", name, self._type_id, exc
                )

    def on_like(self, *args: Any, **kwargs: Any) -> None:
        self._each("on_like", *args, **kwargs)

    def on_share(self, *args: Any, **kwargs: Any) -> None:
        self._each("on_share", *args, **kwargs)

    def on_gift(self, *args: Any, **kwargs: Any) -> None:
        self._each("on_gift", *args, **kwargs)

    def on_comment(self, *args: Any, **kwargs: Any) -> None:
        self._each("on_comment", *args, **kwargs)

    def on_follow(self, *args: Any, **kwargs: Any) -> None:
        self._each("on_follow", *args, **kwargs)

    def reset_for_new_stream(self) -> None:
        self._each("reset_for_new_stream")

    def schedule_publish(self) -> None:
        self._each("schedule_publish")
