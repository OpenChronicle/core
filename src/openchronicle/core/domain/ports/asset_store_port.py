from __future__ import annotations

from abc import ABC, abstractmethod

from openchronicle.core.domain.models.asset import Asset, AssetLink


class AssetStorePort(ABC):
    @abstractmethod
    def add_asset(self, asset: Asset) -> None: ...

    @abstractmethod
    def get_asset(self, asset_id: str) -> Asset | None: ...

    @abstractmethod
    def get_asset_by_hash(self, project_id: str, content_hash: str) -> Asset | None: ...

    @abstractmethod
    def list_assets(self, project_id: str, limit: int | None = None) -> list[Asset]: ...

    @abstractmethod
    def delete_asset(self, asset_id: str) -> bool: ...

    @abstractmethod
    def add_asset_link(self, link: AssetLink) -> None: ...

    @abstractmethod
    def list_asset_links(
        self,
        *,
        asset_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
    ) -> list[AssetLink]: ...

    @abstractmethod
    def delete_asset_link(self, link_id: str) -> bool: ...
