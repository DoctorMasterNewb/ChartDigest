"""add episode state versions"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_episode_state_versions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "episode_state_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("canonical_state_json", sa.JSON(), nullable=False),
        sa.Column("diff_json", sa.JSON(), nullable=True),
        sa.Column("stability_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "version_number", name="uq_episode_state_case_version"),
    )
    op.create_index("ix_episode_state_versions_case_id", "episode_state_versions", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_episode_state_versions_case_id", table_name="episode_state_versions")
    op.drop_table("episode_state_versions")
