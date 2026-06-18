"""add posts_summary to analyses

Revision ID: 2ed4f488c54f
Revises: 02dd7b7c87a1
Create Date: 2026-06-18 15:53:39.811752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ed4f488c54f'
down_revision: Union[str, Sequence[str], None] = '02dd7b7c87a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('analyses', sa.Column('posts_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('analyses', 'posts_summary')
    # ### end Alembic commands ###
