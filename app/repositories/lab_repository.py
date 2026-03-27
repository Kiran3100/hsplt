"""
Lab Repository - Database operations for lab test catalogue (categories + tests).
All queries are scoped by hospital_id for multi-tenant isolation.
"""
from uuid import UUID
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, or_, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lab import LabTestCategory, LabTest
from app.core.enums import LabTestStatus


class LabCatalogueRepository:
    """Repository for lab test categories and test master (catalogue)."""

    def __init__(self, db: AsyncSession, hospital_id: UUID):
        self.db = db
        self.hospital_id = hospital_id

    # -------------------------------------------------------------------------
    # Categories
    # -------------------------------------------------------------------------

    async def get_category_by_id(self, category_id: UUID) -> Optional[LabTestCategory]:
        """Get category by ID, hospital-scoped."""
        result = await self.db.execute(
            select(LabTestCategory).where(
                and_(
                    LabTestCategory.id == category_id,
                    LabTestCategory.hospital_id == self.hospital_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_category_by_code(self, category_code: str) -> Optional[LabTestCategory]:
        """Get category by code, hospital-scoped."""
        result = await self.db.execute(
            select(LabTestCategory).where(
                and_(
                    LabTestCategory.hospital_id == self.hospital_id,
                    LabTestCategory.category_code == category_code.upper().strip(),
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_categories(
        self,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LabTestCategory]:
        """List categories for hospital, optional active filter."""
        conditions = [LabTestCategory.hospital_id == self.hospital_id]
        if active_only:
            conditions.append(LabTestCategory.is_active == True)
        result = await self.db.execute(
            select(LabTestCategory)
            .where(and_(*conditions))
            .order_by(asc(LabTestCategory.display_order), asc(LabTestCategory.name))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_categories(self, active_only: bool = True) -> int:
        """Count categories for hospital."""
        conditions = [LabTestCategory.hospital_id == self.hospital_id]
        if active_only:
            conditions.append(LabTestCategory.is_active == True)
        result = await self.db.execute(select(func.count(LabTestCategory.id)).where(and_(*conditions)))
        return result.scalar() or 0

    async def create_category(self, category: LabTestCategory) -> LabTestCategory:
        """Persist new category."""
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def update_category(self, category: LabTestCategory) -> LabTestCategory:
        """Refresh category after update."""
        await self.db.flush()
        await self.db.refresh(category)
        return category

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    async def get_test_by_id(self, test_id: UUID) -> Optional[LabTest]:
        """Get test by ID, hospital-scoped; loads category."""
        result = await self.db.execute(
            select(LabTest)
            .options(selectinload(LabTest.category))
            .where(
                and_(
                    LabTest.id == test_id,
                    LabTest.hospital_id == self.hospital_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_test_by_code(self, test_code: str) -> Optional[LabTest]:
        """Get test by code, hospital-scoped."""
        result = await self.db.execute(
            select(LabTest).where(
                and_(
                    LabTest.hospital_id == self.hospital_id,
                    LabTest.test_code == test_code.upper().strip(),
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_tests(
        self,
        active_only: bool = True,
        category_id: Optional[UUID] = None,
        sample_type: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[LabTest]:
        """List tests with filters and search; ordered by test_name."""
        conditions = [LabTest.hospital_id == self.hospital_id]
        if active_only:
            conditions.append(LabTest.is_active == True)
        if category_id is not None:
            conditions.append(LabTest.category_id == category_id)
        if sample_type:
            conditions.append(LabTest.sample_type == sample_type)
        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append(
                or_(
                    LabTest.test_code.ilike(term),
                    LabTest.test_name.ilike(term),
                )
            )
        result = await self.db.execute(
            select(LabTest)
            .options(selectinload(LabTest.category))
            .where(and_(*conditions))
            .order_by(asc(LabTest.test_name))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_tests(
        self,
        active_only: bool = True,
        category_id: Optional[UUID] = None,
        sample_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count tests with same filters as list_tests."""
        conditions = [LabTest.hospital_id == self.hospital_id]
        if active_only:
            conditions.append(LabTest.is_active == True)
        if category_id is not None:
            conditions.append(LabTest.category_id == category_id)
        if sample_type:
            conditions.append(LabTest.sample_type == sample_type)
        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append(
                or_(
                    LabTest.test_code.ilike(term),
                    LabTest.test_name.ilike(term),
                )
            )
        result = await self.db.execute(select(func.count(LabTest.id)).where(and_(*conditions)))
        return result.scalar() or 0

    async def create_test(self, test: LabTest) -> LabTest:
        """Persist new test."""
        self.db.add(test)
        await self.db.flush()
        await self.db.refresh(test)
        return test

    async def update_test(self, test: LabTest) -> LabTest:
        """Refresh test after update."""
        await self.db.flush()
        await self.db.refresh(test)
        return test
