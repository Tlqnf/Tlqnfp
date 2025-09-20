"""Merge heads

Revision ID: 90c2ef11529f
Revises: 34bd9ac3af64, 37898715e0f0
Create Date: 2025-09-18 13:10:32.140042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90c2ef11529f'
down_revision: Union[str, Sequence[str], None] = ('34bd9ac3af64', '37898715e0f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
