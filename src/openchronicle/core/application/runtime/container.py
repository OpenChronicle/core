from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from openchronicle.core.application.runtime.plugin_loader import PluginLoader
from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry
from openchronicle.core.application.services.orchestrator import OrchestratorService
from openchronicle.core.domain.errors.error_codes import CONFIG_ERROR
from openchronicle.core.domain.ports.llm_port import LLMPort, LLMProviderError
from openchronicle.core.domain.ports.router_assist_port import RouterAssistPort
from openchronicle.core.infrastructure.config.settings import (
    load_privacy_outbound_settings,
    load_router_assist_settings,
)
from openchronicle.core.infrastructure.llm.provider_facade import create_provider_aware_llm
from openchronicle.core.infrastructure.logging.event_logger import EventLogger
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore
from openchronicle.core.infrastructure.privacy.rule_privacy import RulePrivacyGate
from openchronicle.core.infrastructure.router_assist import LinearRouterAssist, OnnxRouterAssist
from openchronicle.core.infrastructure.routing.hybrid_router import HybridInteractionRouter
from openchronicle.core.infrastructure.routing.rule_router import RuleInteractionRouter


class CoreContainer:
    def __init__(
        self,
        db_path: str | None = None,
        config_dir: str | None = None,
        plugin_dir: str | None = None,
        output_dir: str | None = None,
        llm: LLMPort | None = None,
    ) -> None:
        db_path_str = db_path if db_path is not None else os.getenv("OC_DB_PATH", "data/openchronicle.db")
        config_dir_str = config_dir if config_dir is not None else os.getenv("OC_CONFIG_DIR", "config")
        plugin_dir_str = plugin_dir if plugin_dir is not None else os.getenv("OC_PLUGIN_DIR", "plugins")
        output_dir_str = output_dir if output_dir is not None else os.getenv("OC_OUTPUT_DIR", "output")

        db_path_resolved = Path(db_path_str)
        config_dir_resolved = Path(config_dir_str)
        plugin_dir_resolved = Path(plugin_dir_str)
        output_dir_resolved = Path(output_dir_str)

        db_path_resolved.parent.mkdir(parents=True, exist_ok=True)
        if not config_dir_resolved.exists():
            raise LLMProviderError(
                f"Config directory not found: {config_dir_resolved}",
                error_code=CONFIG_ERROR,
                hint="Run `oc init` or create the directory.",
                details={"config_dir": str(config_dir_resolved)},
            )
        plugin_dir_resolved.mkdir(parents=True, exist_ok=True)
        output_dir_resolved.mkdir(parents=True, exist_ok=True)

        self.storage = SqliteStore(db_path=str(db_path_resolved))
        self.storage.init_schema()
        self.event_logger = EventLogger(self.storage)
        self.privacy_gate = RulePrivacyGate()
        self.privacy_settings = load_privacy_outbound_settings()
        router_assist_settings = load_router_assist_settings()

        # Use provider-aware facade if no explicit LLM provided
        if llm is None:
            # Create facade that can route to multiple providers
            llm = create_provider_aware_llm(config_dir=config_dir_str)

        self.llm = llm

        assist: RouterAssistPort | None = None
        if router_assist_settings.enabled:
            if not router_assist_settings.model_path:
                raise LLMProviderError(
                    "Router assist model path not configured",
                    error_code=CONFIG_ERROR,
                    hint="Set OC_ROUTER_ASSIST_MODEL_PATH to a model JSON file.",
                )
            backend = router_assist_settings.backend.lower()
            if backend == "linear":
                assist = LinearRouterAssist(
                    model_path=router_assist_settings.model_path,
                    timeout_ms=router_assist_settings.timeout_ms,
                )
            elif backend == "onnx":
                assist = OnnxRouterAssist(
                    model_path=router_assist_settings.model_path,
                    timeout_ms=router_assist_settings.timeout_ms,
                )
            else:
                raise LLMProviderError(
                    f"Unsupported router assist backend: {router_assist_settings.backend}",
                    error_code=CONFIG_ERROR,
                    hint="Set OC_ROUTER_ASSIST_BACKEND to 'linear' or 'onnx'.",
                )

        self.interaction_router = HybridInteractionRouter(base_router=RuleInteractionRouter(), assist=assist)
        self.handler_registry = TaskHandlerRegistry()
        self.plugin_loader = PluginLoader(plugins_dir=str(plugin_dir_resolved), handler_registry=self.handler_registry)
        self.plugin_loader.load_plugins()
        self.orchestrator = OrchestratorService(
            storage=self.storage,
            llm=self.llm,
            plugins=self.plugin_loader.registry_instance(),
            handler_registry=self.plugin_loader.handler_registry_instance(),
            emit_event=self.event_logger.append,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "storage": self.storage,
            "event_logger": self.event_logger,
            "privacy_gate": self.privacy_gate,
            "privacy_settings": self.privacy_settings,
            "llm": self.llm,
            "interaction_router": self.interaction_router,
            "plugins": self.plugin_loader.registry_instance(),
            "handler_registry": self.plugin_loader.handler_registry_instance(),
            "orchestrator": self.orchestrator,
        }
