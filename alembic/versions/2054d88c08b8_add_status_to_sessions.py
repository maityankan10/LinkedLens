"""add status to sessions

Revision ID: 2054d88c08b8
Revises: 1f2381deb382
Create Date: 2026-06-21 13:32:58.895250

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '2054d88c08b8'
down_revision: Union[str, Sequence[str], None] = '1f2381deb382'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('sessions', sa.Column('status', sa.String(length=20), nullable=False, server_default='ready'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sessions', 'status')
    op.create_table('feedbacks',
    sa.Column('id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('session_id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('helpful', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
    sa.Column('comment', mysql.TEXT(), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('feedbacks_ibfk_1')),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index(op.f('ix_feedbacks_session_id'), 'feedbacks', ['session_id'], unique=False)
    # ### end Alembic commands ###
