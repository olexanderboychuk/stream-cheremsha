from __future__ import annotations

from typing import Any

from stream_cheremsha.overlays import live_leaderboard_simple_config as simple_cfg_mod
from stream_cheremsha.overlays.live_leaderboard_controller import LiveLeaderboardController
from stream_cheremsha.overlays.live_leaderboard_ranking import ContributorWeights
from stream_cheremsha.overlays.live_leaderboard_rotation import filter_sequence_for_config


class LiveLeaderboardSimpleController(LiveLeaderboardController):
    OVERLAY_TYPE = "live_leaderboard_simple"

    def _load_cfg(self):  # noqa: ANN202
        return simple_cfg_mod.load_live_leaderboard_simple_config()

    def _public_dict(self, cfg) -> dict[str, Any]:  # noqa: ANN001, ANN202
        return simple_cfg_mod.live_leaderboard_simple_config_to_public_dict(cfg)

    def _reload_config(self, *, reset_rotation: bool) -> None:
        cfg = self._load_cfg()
        self._ranking.weights = ContributorWeights(
            like=cfg.weight_like,
            gift_coin=cfg.weight_gift_coin,
            share=cfg.weight_share,
            comment=cfg.weight_comment,
        )
        steps = filter_sequence_for_config(
            simple_cfg_mod.parse_sequence_steps(cfg),
            enabled_sources=simple_cfg_mod.enabled_sources_from_config(cfg),
            enabled_scenes=simple_cfg_mod.enabled_scenes_from_config(cfg),
        )
        if reset_rotation:
            self._rotation.replace_sequence(steps, preserve_position=False)
        else:
            self._rotation.replace_sequence(steps, preserve_position=True)

    def _build_state(self) -> dict[str, Any]:
        import time

        cfg = self._load_cfg()
        now_ms = int(time.time() * 1000)
        return {
            "config": self._public_dict(cfg),
            "rankings": self._ranking.all_rankings(limit=cfg.top_n),
            "presentation": self._rotation.presentation_dict(server_now_ms=now_ms),
            "locale": str(self._get_locale() or "uk"),
        }
