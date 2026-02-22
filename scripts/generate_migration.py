"""Generate Alembic migration from station CSV files.

Usage:
    # Full insert (initial seed):
    cd backend && poetry run python ../scripts/generate_migration.py data/stations_20260222.csv

    # Diff update (add/remove stations):
    cd backend && poetry run python ../scripts/generate_migration.py data/stations_old.csv data/stations_new.csv

Output:
    backend/alembic/versions/v{NNN}_{description}.py
"""

import csv
import re
import sys
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_next_version(versions_dir: Path) -> tuple[str, str]:
    """Find the next version number and the current latest revision."""
    existing = []
    for f in versions_dir.glob("v*_*.py"):
        match = re.match(r"v(\d+)_", f.name)
        if match:
            existing.append(int(match.group(1)))

    if not existing:
        return "002", "001"

    latest = max(existing)
    next_num = latest + 1
    return f"{next_num:03d}", f"{latest:03d}"


def generate_full_insert(
    rows: list[dict[str, str]], revision: str, down_revision: str
) -> str:
    """Generate migration for full insert of all stations."""
    values_lines = []
    delete_keys = []
    for row in rows:
        prec_no = int(row["prec_no"])
        name = row["station_name"].replace("'", "''")
        block_no = row["block_no"]
        stype = row["station_type"]
        values_lines.append(f"            ('{name}', {prec_no}, '{block_no}', '{stype}')")
        delete_keys.append(f"            ({prec_no}, '{block_no}')")

    values_sql = ",\n".join(values_lines)
    delete_sql = ",\n".join(delete_keys)

    return f'''"""seed all stations

Revision ID: {revision}
Revises: {down_revision}
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "{revision}"
down_revision: Union[str, None] = "{down_revision}"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            INSERT INTO heat.stations (station_name, prec_no, block_no, station_type)
            VALUES
{values_sql}
            ON CONFLICT ON CONSTRAINT uq_stations_prec_block DO NOTHING
        """)
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            DELETE FROM heat.stations
            WHERE (prec_no, block_no) IN (
{delete_sql}
            )
            AND id NOT IN (SELECT DISTINCT station_id FROM heat.daily_temperature)
        """)
    )
'''


def generate_diff(
    old_rows: list[dict[str, str]],
    new_rows: list[dict[str, str]],
    revision: str,
    down_revision: str,
) -> str | None:
    """Generate migration for diff between old and new CSV."""
    old_keys = {(int(r["prec_no"]), r["block_no"]): r for r in old_rows}
    new_keys = {(int(r["prec_no"]), r["block_no"]): r for r in new_rows}

    to_add = {k: new_keys[k] for k in new_keys if k not in old_keys}
    to_remove = {k: old_keys[k] for k in old_keys if k not in new_keys}

    if not to_add and not to_remove:
        return None

    upgrade_parts = []
    downgrade_parts = []

    if to_add:
        values_lines = []
        delete_keys = []
        for (prec_no, block_no), row in sorted(to_add.items()):
            name = row["station_name"].replace("'", "''")
            stype = row["station_type"]
            values_lines.append(
                f"            ('{name}', {prec_no}, '{block_no}', '{stype}')"
            )
            delete_keys.append(f"            ({prec_no}, '{block_no}')")

        values_sql = ",\n".join(values_lines)
        delete_sql = ",\n".join(delete_keys)

        upgrade_parts.append(
            f"""    conn.execute(
        sa.text(\"\"\"
            INSERT INTO heat.stations (station_name, prec_no, block_no, station_type)
            VALUES
{values_sql}
            ON CONFLICT ON CONSTRAINT uq_stations_prec_block DO NOTHING
        \"\"\")
    )"""
        )

        downgrade_parts.append(
            f"""    conn.execute(
        sa.text(\"\"\"
            DELETE FROM heat.stations
            WHERE (prec_no, block_no) IN (
{delete_sql}
            )
            AND id NOT IN (SELECT DISTINCT station_id FROM heat.daily_temperature)
        \"\"\")
    )"""
        )

    if to_remove:
        delete_keys = []
        reinsert_lines = []
        for (prec_no, block_no), row in sorted(to_remove.items()):
            name = row["station_name"].replace("'", "''")
            stype = row["station_type"]
            delete_keys.append(f"            ({prec_no}, '{block_no}')")
            reinsert_lines.append(
                f"            ('{name}', {prec_no}, '{block_no}', '{stype}')"
            )

        delete_sql = ",\n".join(delete_keys)
        reinsert_sql = ",\n".join(reinsert_lines)

        upgrade_parts.append(
            f"""    conn.execute(
        sa.text(\"\"\"
            DELETE FROM heat.stations
            WHERE (prec_no, block_no) IN (
{delete_sql}
            )
            AND id NOT IN (SELECT DISTINCT station_id FROM heat.daily_temperature)
        \"\"\")
    )"""
        )

        downgrade_parts.append(
            f"""    conn.execute(
        sa.text(\"\"\"
            INSERT INTO heat.stations (station_name, prec_no, block_no, station_type)
            VALUES
{reinsert_sql}
            ON CONFLICT ON CONSTRAINT uq_stations_prec_block DO NOTHING
        \"\"\")
    )"""
        )

    upgrade_body = "\n\n".join(upgrade_parts)
    downgrade_body = "\n\n".join(downgrade_parts)

    added = len(to_add)
    removed = len(to_remove)
    desc_parts = []
    if added:
        desc_parts.append(f"add {added} stations")
    if removed:
        desc_parts.append(f"remove {removed} stations")
    description = " and ".join(desc_parts)

    return f'''"""{description}

Revision ID: {revision}
Revises: {down_revision}
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "{revision}"
down_revision: Union[str, None] = "{down_revision}"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
{upgrade_body}


def downgrade() -> None:
    conn = op.get_bind()
{downgrade_body}
'''


def main() -> None:
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage:")
        print("  Full insert:  python generate_migration.py <csv>")
        print("  Diff update:  python generate_migration.py <old_csv> <new_csv>")
        sys.exit(1)

    versions_dir = Path("alembic/versions")
    if not versions_dir.exists():
        print("Error: alembic/versions not found. Run from the backend/ directory.")
        sys.exit(1)

    revision, down_revision = find_next_version(versions_dir)

    if len(sys.argv) == 2:
        csv_path = Path(sys.argv[1])
        rows = read_csv(csv_path)
        print(f"Read {len(rows)} stations from {csv_path}")

        content = generate_full_insert(rows, revision, down_revision)
        description = "seed_all_stations"
    else:
        old_path = Path(sys.argv[1])
        new_path = Path(sys.argv[2])
        old_rows = read_csv(old_path)
        new_rows = read_csv(new_path)
        print(f"Old: {len(old_rows)} stations, New: {len(new_rows)} stations")

        content = generate_diff(old_rows, new_rows, revision, down_revision)
        if content is None:
            print("No changes detected between CSVs.")
            return
        description = "update_stations"

    output_path = versions_dir / f"v{revision}_{description}.py"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated migration: {output_path}")


if __name__ == "__main__":
    main()
