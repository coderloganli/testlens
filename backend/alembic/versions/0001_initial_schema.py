"""Drive telemetry and failure-prediction tables

Revision ID: 0001
Revises:
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drives",
        sa.Column("serial_number", sa.String(64), primary_key=True),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("capacity_bytes", sa.BigInteger(), nullable=False),
        sa.Column("datacenter", sa.String(32), nullable=False),
        sa.Column("deployed_on", sa.Date(), nullable=False),
        sa.Column("failed_on", sa.Date(), nullable=True),
    )
    op.create_index("ix_drives_model", "drives", ["model"])

    op.create_table(
        "smart_readings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "serial_number",
            sa.String(64),
            sa.ForeignKey("drives.serial_number"),
            nullable=False,
        ),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("power_on_hours", sa.Integer(), nullable=False),
        sa.Column("reallocated_sectors", sa.Integer(), nullable=False),
        sa.Column("reported_uncorrectable", sa.Integer(), nullable=False),
        sa.Column("command_timeouts", sa.Integer(), nullable=False),
        sa.Column("pending_sectors", sa.Integer(), nullable=False),
        sa.Column("offline_uncorrectable", sa.Integer(), nullable=False),
        sa.Column("temperature_c", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_smart_readings_drive_day", "smart_readings", ["serial_number", "observed_on"]
    )

    op.create_table(
        "failure_predictions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "serial_number",
            sa.String(64),
            sa.ForeignKey("drives.serial_number"),
            nullable=False,
        ),
        sa.Column("scored_on", sa.Date(), nullable=False),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("failure_probability", sa.Float(), nullable=False),
    )
    op.create_index(
        "ix_failure_predictions_drive_day", "failure_predictions", ["serial_number", "scored_on"]
    )


def downgrade() -> None:
    op.drop_table("failure_predictions")
    op.drop_table("smart_readings")
    op.drop_index("ix_drives_model", table_name="drives")
    op.drop_table("drives")
