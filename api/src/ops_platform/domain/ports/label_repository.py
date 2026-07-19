from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import Label


class LabelRepository(ABC):
    """Port for label persistence. A label always belongs to exactly one project;
    naming is unique per project (see uq_labels_project_id_name)."""

    @abstractmethod
    async def create(self, project_id: UUID, name: str, color: str) -> Label: ...

    @abstractmethod
    async def get(self, label_id: UUID) -> Label | None: ...

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[Label]: ...
