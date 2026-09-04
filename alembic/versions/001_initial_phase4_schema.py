"""Initial Phase 4 Multi-Campus Schema

Revision ID: 001_initial_phase4
Revises: 
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_phase4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema creation is handled safely via Base.metadata.create_all on async engine startup
    pass


def downgrade() -> None:
    pass
