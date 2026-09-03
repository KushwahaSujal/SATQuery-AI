"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-30 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. analysis_jobs
    op.create_table(
        'analysis_jobs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('task_type', sa.String(length=64), nullable=True),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_analysis_jobs'))
    )
    op.create_index(op.f('ix_analysis_jobs_created_at'), 'analysis_jobs', ['created_at'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_status'), 'analysis_jobs', ['status'], unique=False)

    # 2. uploaded_files
    op.create_table(
        'uploaded_files',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('job_id', sa.String(length=64), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_path', sa.Text(), nullable=False),
        sa.Column('mime_type', sa.String(length=128), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('band_count', sa.Integer(), nullable=True),
        sa.Column('crs', sa.String(length=128), nullable=True),
        sa.Column('bounds', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], name=op.f('fk_uploaded_files_job_id_analysis_jobs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_uploaded_files'))
    )
    op.create_index(op.f('ix_uploaded_files_job_id'), 'uploaded_files', ['job_id'], unique=False)

    # 3. model_runs
    op.create_table(
        'model_runs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('job_id', sa.String(length=64), nullable=False),
        sa.Column('model_name', sa.String(length=128), nullable=False),
        sa.Column('model_version', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('device', sa.String(length=64), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], name=op.f('fk_model_runs_job_id_analysis_jobs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_model_runs'))
    )
    op.create_index(op.f('ix_model_runs_job_id'), 'model_runs', ['job_id'], unique=False)

    # 4. execution_steps
    op.create_table(
        'execution_steps',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('job_id', sa.String(length=64), nullable=False),
        sa.Column('step_name', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('model_name', sa.String(length=128), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], name=op.f('fk_execution_steps_job_id_analysis_jobs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_execution_steps'))
    )
    op.create_index(op.f('ix_execution_steps_job_id'), 'execution_steps', ['job_id'], unique=False)

    # 5. analysis_results
    op.create_table(
        'analysis_results',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('job_id', sa.String(length=64), nullable=False),
        sa.Column('answer', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('result_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], name=op.f('fk_analysis_results_job_id_analysis_jobs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_analysis_results'))
    )
    op.create_index(op.f('ix_analysis_results_job_id'), 'analysis_results', ['job_id'], unique=False)

    # 6. artifacts
    op.create_table(
        'artifacts',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('job_id', sa.String(length=64), nullable=False),
        sa.Column('artifact_type', sa.String(length=64), nullable=False),
        sa.Column('filesystem_path', sa.Text(), nullable=False),
        sa.Column('mime_type', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], name=op.f('fk_artifacts_job_id_analysis_jobs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_artifacts'))
    )
    op.create_index(op.f('ix_artifacts_job_id'), 'artifacts', ['job_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_artifacts_job_id'), table_name='artifacts')
    op.drop_table('artifacts')

    op.drop_index(op.f('ix_analysis_results_job_id'), table_name='analysis_results')
    op.drop_table('analysis_results')

    op.drop_index(op.f('ix_execution_steps_job_id'), table_name='execution_steps')
    op.drop_table('execution_steps')

    op.drop_index(op.f('ix_model_runs_job_id'), table_name='model_runs')
    op.drop_table('model_runs')

    op.drop_index(op.f('ix_uploaded_files_job_id'), table_name='uploaded_files')
    op.drop_table('uploaded_files')

    op.drop_index(op.f('ix_analysis_jobs_status'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_created_at'), table_name='analysis_jobs')
    op.drop_table('analysis_jobs')
