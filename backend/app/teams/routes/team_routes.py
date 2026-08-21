from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import UserRole
from app.models.attachment import Department, Team
from app.teams.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    TeamCreate,
    TeamResponse,
)

router = APIRouter(prefix="/teams", tags=["Teams & Departments"])


# ─── Department Endpoints ────────────────────────────────────────────────────────

@router.get(
    "/departments",
    response_model=list[DepartmentResponse],
    summary="List all departments",
)
async def list_departments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Department).order_by(Department.name))
    departments = result.scalars().all()
    return departments


@router.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department (Admin only)",
)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.ADMIN)),
):
    # Check for duplicate name
    existing = await db.execute(
        select(Department).where(Department.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department with this name already exists",
        )

    department = Department(name=data.name)
    db.add(department)
    await db.flush()
    await db.refresh(department)
    return department


@router.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a department (Admin only)",
)
async def delete_department(
    department_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )
    await db.delete(department)


# ─── Team Endpoints ──────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[TeamResponse],
    summary="List all teams",
)
async def list_teams(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Team).order_by(Team.name))
    teams = result.scalars().all()
    return teams


@router.post(
    "/",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a team (Admin only)",
)
async def create_team(
    data: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.ADMIN)),
):
    # Verify department exists
    dept_result = await db.execute(
        select(Department).where(Department.id == data.department_id)
    )
    if not dept_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department not found",
        )

    # Check for duplicate team name within the same department
    existing = await db.execute(
        select(Team).where(Team.name == data.name, Team.department_id == data.department_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Team with this name already exists in this department",
        )

    team = Team(name=data.name, department_id=data.department_id)
    db.add(team)
    await db.flush()
    await db.refresh(team)
    return team


@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a team (Admin only)",
)
async def delete_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )
    await db.delete(team)
