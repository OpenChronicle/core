"""Port for webhook subscription and delivery persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from openchronicle.core.domain.models.webhook import DeliveryAttempt, WebhookSubscription


class WebhookStorePort(ABC):
    @abstractmethod
    def add_subscription(self, sub: WebhookSubscription) -> None: ...

    @abstractmethod
    def get_subscription(self, sub_id: str) -> WebhookSubscription | None: ...

    @abstractmethod
    def list_subscriptions(
        self, project_id: str | None = None, active_only: bool = False
    ) -> list[WebhookSubscription]: ...

    @abstractmethod
    def delete_subscription(self, sub_id: str) -> None: ...

    @abstractmethod
    def update_subscription(
        self,
        sub_id: str,
        *,
        active: bool | None = None,
        url: str | None = None,
        event_filter: str | None = None,
    ) -> None: ...

    @abstractmethod
    def add_delivery(self, attempt: DeliveryAttempt) -> None: ...

    @abstractmethod
    def list_deliveries(self, subscription_id: str, limit: int = 50) -> list[DeliveryAttempt]: ...
