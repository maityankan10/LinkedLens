"""add posts_summary column

Revision ID: 798f98c55f0e
Revises: 2ed4f488c54f
Create Date: 2026-06-18 16:12:27.436229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '798f98c55f0e'
down_revision: Union[str, Sequence[str], None] = '2ed4f488c54f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
