"""002_enable_rls

Revision ID: 002_enable_rls
Revises: 001_initial_schema
Create Date: 2026-09-04 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002_enable_rls'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    'alembic_version',
    'analysis_jobs',
    'uploaded_files',
    'model_runs',
    'execution_steps',
    'analysis_results',
    'artifacts',
]


def upgrade() -> None:
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')


def downgrade() -> None:
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY;')
