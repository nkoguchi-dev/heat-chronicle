"""create initial tables

Revision ID: 001
Revises:
Create Date: 2026-02-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("station_name", sa.String(50), nullable=False),
        sa.Column("prec_no", sa.Integer, nullable=False),
        sa.Column("block_no", sa.String(10), nullable=False),
        sa.Column("station_type", sa.String(1), nullable=False),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.UniqueConstraint("prec_no", "block_no", name="uq_stations_prec_block"),
    )

    op.create_table(
        "daily_temperature",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "station_id",
            sa.Integer,
            sa.ForeignKey("stations.id"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("max_temp", sa.Float, nullable=True),
        sa.Column("min_temp", sa.Float, nullable=True),
        sa.Column("avg_temp", sa.Float, nullable=True),
        sa.UniqueConstraint(
            "station_id", "date", name="uq_daily_temp_station_date"
        ),
        sa.Index("ix_daily_temp_station_date", "station_id", "date"),
    )

    op.create_table(
        "fetch_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "station_id",
            sa.Integer,
            sa.ForeignKey("stations.id"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column(
            "fetched_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "station_id", "year", "month", name="uq_fetch_log_station_year_month"
        ),
    )

    # Seed 12 stations
    stations_table = sa.table(
        "stations",
        sa.column("station_name", sa.String),
        sa.column("prec_no", sa.Integer),
        sa.column("block_no", sa.String),
        sa.column("station_type", sa.String),
    )

    op.bulk_insert(
        stations_table,
        [
            {"station_name": "札幌", "prec_no": 14, "block_no": "47412", "station_type": "s"},
            {"station_name": "仙台", "prec_no": 34, "block_no": "47590", "station_type": "s"},
            {"station_name": "さいたま", "prec_no": 43, "block_no": "0363", "station_type": "a"},
            {"station_name": "東京", "prec_no": 44, "block_no": "47662", "station_type": "s"},
            {"station_name": "新潟", "prec_no": 54, "block_no": "47604", "station_type": "s"},
            {"station_name": "名古屋", "prec_no": 51, "block_no": "47636", "station_type": "s"},
            {"station_name": "大阪", "prec_no": 62, "block_no": "47772", "station_type": "s"},
            {"station_name": "広島", "prec_no": 67, "block_no": "47765", "station_type": "s"},
            {"station_name": "高松", "prec_no": 72, "block_no": "47891", "station_type": "s"},
            {"station_name": "福岡", "prec_no": 82, "block_no": "47807", "station_type": "s"},
            {"station_name": "鹿児島", "prec_no": 88, "block_no": "47827", "station_type": "s"},
            {"station_name": "那覇", "prec_no": 91, "block_no": "47936", "station_type": "s"},
        ],
    )


def downgrade() -> None:
    op.drop_table("fetch_log")
    op.drop_table("daily_temperature")
    op.drop_table("stations")
