from __future__ import annotations

from openchronicle.core.domain.models.conversation import Turn
from openchronicle.core.domain.models.interaction_hint import InteractionHint
from openchronicle.core.domain.ports.interaction_router_port import InteractionRouterPort
from openchronicle.core.domain.ports.router_assist_port import RouterAssistPort


class HybridInteractionRouter(InteractionRouterPort):
    def __init__(self, *, base_router: InteractionRouterPort, assist: RouterAssistPort | None = None) -> None:
        self._base_router = base_router
        self._assist = assist

    def analyze(self, *, user_text: str, recent_turns: list[Turn] | None = None) -> InteractionHint:
        base_hint = self._base_router.analyze(user_text=user_text, recent_turns=recent_turns)
        if self._assist is None:
            return base_hint

        assist_result = self._assist.analyze(user_text, base_hint.mode_hint)

        # Deterministic combination: keep base router score unless assist reports higher risk.
        final_nsfw_score = max(base_hint.nsfw_score, assist_result.nsfw_probability)
        requires_nsfw = _requires_nsfw_capable_model(self._base_router, base_hint.mode_hint, final_nsfw_score)

        reason_codes = []
        if getattr(self._base_router, "router_log_reasons", False):
            reason_codes = list(base_hint.reason_codes) + list(assist_result.reason_codes)

        return InteractionHint(
            mode_hint=base_hint.mode_hint,
            nsfw_score=final_nsfw_score,
            requires_nsfw_capable_model=requires_nsfw,
            reason_codes=reason_codes,
        )


def _requires_nsfw_capable_model(router: InteractionRouterPort, mode_hint: str, nsfw_score: float) -> bool:
    nsfw_route_if_score_gte = getattr(router, "nsfw_route_if_score_gte", 0.70)
    nsfw_uncertain_if_score_gte = getattr(router, "nsfw_uncertain_if_score_gte", 0.45)
    persona_uncertain_routes_to_nsfw = getattr(router, "persona_uncertain_routes_to_nsfw", True)

    if nsfw_score >= nsfw_route_if_score_gte:
        return True
    return (
        nsfw_score >= nsfw_uncertain_if_score_gte
        and mode_hint in {"persona", "story"}
        and persona_uncertain_routes_to_nsfw
    )
