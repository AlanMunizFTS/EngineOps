from typing import Any
from uuid import UUID

from ops_platform.application.errors import NotFoundError
from ops_platform.domain.entities import Milestone, MilestoneStatus
from ops_platform.domain.ports.milestone_repository import MilestoneRepository


class MilestoneService:
    def __init__(self, milestones: MilestoneRepository) -> None:
        self.milestones = milestones

    async def create(self, **values: Any) -> Milestone:
        values.setdefault("status", MilestoneStatus.OPEN)
        return await self.milestones.create(**values)

    async def get(self, milestone_id: UUID) -> Milestone:
        milestone = await self.milestones.get(milestone_id)
        if milestone is None:
            raise NotFoundError("Milestone not found")
        return milestone

    async def list_for_project(self, project_id: UUID) -> list[Milestone]:
        return await self.milestones.list_for_project(project_id)

    async def update(self, milestone_id: UUID, **changes: Any) -> Milestone:
        await self.get(milestone_id)
        return await self.milestones.update(milestone_id, **changes)

    async def delete(self, milestone_id: UUID) -> Milestone:
        milestone = await self.get(milestone_id)
        await self.milestones.delete(milestone_id)
        return milestone

    async def calculate_progress(self, milestone_id: UUID) -> tuple[int, int, float]:
        milestone = await self.get(milestone_id)
        return (
            milestone.completed_tasks,
            milestone.total_tasks,
            milestone.progress_percentage,
        )
