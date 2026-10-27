"""Import California's tab-delimited public data dump into SQLite."""

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import sqlite3

from sqlalchemy import create_engine

from .models import Base


log = logging.getLogger("openstates.ca.sqlite")
SCHEMA_VERSION = 1

TABLES = (
    "bill_tbl",
    "bill_version_tbl",
    "bill_version_authors_tbl",
    "bill_analysis_tbl",
    "bill_history_tbl",
    "bill_motion_tbl",
    "location_code_tbl",
    "bill_summary_vote_tbl",
    "bill_detail_vote_tbl",
    "committee_hearing_tbl",
)

INDEXES = (
    ("ix_bill_session_type", "bill_tbl", "session_year, measure_type"),
    ("ix_version_bill", "bill_version_tbl", "bill_id, version_num"),
    ("ix_author_version", "bill_version_authors_tbl", "bill_version_id"),
    ("ix_analysis_bill", "bill_analysis_tbl", "bill_id, analysis_date"),
    ("ix_history_bill", "bill_history_tbl", "bill_id, bill_history_id"),
    ("ix_summary_bill", "bill_summary_vote_tbl", "bill_id, vote_date_time"),
    (
        "ix_detail_summary",
        "bill_detail_vote_tbl",
        "bill_id, location_code, vote_date_time, vote_date_seq, motion_id",
    ),
    (
        "ix_location_session_code",
        "location_code_tbl",
        "session_year, location_code",
    ),
    (
        "ix_hearing_location_date",
        "committee_hearing_tbl",
        "location_code, hearing_date",
    ),
)


def _dump_signature(data_dir):
    files = []
    for table_name in TABLES:
        path = data_dir / f"{table_name.upper()}.dat"
        stat = path.stat()
        files.append((path.name, stat.st_size, stat.st_mtime_ns))
    return hashlib.sha256(json.dumps([SCHEMA_VERSION, files]).encode()).hexdigest()


def _database_signature(database_path):
    if not database_path.exists():
        return None
    try:
        with sqlite3.connect(database_path) as connection:
            row = connection.execute(
                "SELECT value FROM ca_import_metadata WHERE key = 'dump_signature'"
            ).fetchone()
            return row[0] if row else None
    except sqlite3.DatabaseError:
        return None


def _decode_cell(cell):
    if cell == "NULL":
        return None
    if len(cell) >= 2 and cell[0] == "`" and cell[-1] == "`":
        return cell[1:-1]
    return cell


def _rows(data_dir, table_name, column_count):
    path = data_dir / f"{table_name.upper()}.dat"
    with path.open(encoding="utf-8", errors="replace") as source:
        for line_number, line in enumerate(source, 1):
            cells = [_decode_cell(cell) for cell in line.rstrip("\r\n").split("\t")]
            if len(cells) < column_count:
                raise ValueError(
                    f"{path}:{line_number} has {len(cells)} columns; "
                    f"expected at least {column_count}"
                )
            cells = cells[:column_count]

            if table_name == "bill_version_tbl" and cells[14]:
                lob_path = data_dir / cells[14]
                cells[14] = lob_path.read_text(encoding="utf-8", errors="replace")
            elif table_name == "bill_analysis_tbl":
                # The scraper builds analysis URLs from metadata and never reads
                # the PDF/RTF body. Omitting it saves roughly 1 GiB per snapshot.
                cells[10] = None

            yield cells


def _insert_table(connection, data_dir, table_name, batch_size=5000):
    table = Base.metadata.tables[table_name]
    columns = [column.name for column in table.columns]
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO {table_name} ({', '.join(columns)}) " f"VALUES ({placeholders})"

    batch = []
    count = 0
    for row in _rows(data_dir, table_name, len(columns)):
        batch.append(row)
        if len(batch) >= batch_size:
            connection.executemany(sql, batch)
            count += len(batch)
            batch.clear()
    if batch:
        connection.executemany(sql, batch)
        count += len(batch)
    log.info("loaded %s rows into %s", count, table_name)
    return count


def import_sqlite_database(data_dir, database_path):
    data_dir = Path(data_dir).expanduser().resolve()
    database_path = Path(database_path).expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = database_path.with_name(f".{database_path.name}.tmp")

    if temporary_path.exists():
        temporary_path.unlink()

    engine = create_engine(f"sqlite:///{temporary_path}")
    Base.metadata.create_all(engine)
    engine.dispose()

    try:
        with sqlite3.connect(temporary_path) as connection:
            connection.execute("PRAGMA journal_mode = OFF")
            connection.execute("PRAGMA synchronous = OFF")
            connection.execute("PRAGMA temp_store = MEMORY")
            connection.execute("PRAGMA cache_size = -200000")

            for table_name in TABLES:
                _insert_table(connection, data_dir, table_name)

            for name, table_name, columns in INDEXES:
                connection.execute(f"CREATE INDEX {name} ON {table_name} ({columns})")

            connection.execute(
                "CREATE TABLE ca_import_metadata "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO ca_import_metadata VALUES (?, ?)",
                ("dump_signature", _dump_signature(data_dir)),
            )
            connection.execute("ANALYZE")
            connection.commit()

        os.replace(temporary_path, database_path)
    except BaseException:
        if temporary_path.exists():
            temporary_path.unlink()
        raise

    return database_path


def ensure_sqlite_database(data_dir, database_path):
    data_dir = Path(data_dir).expanduser().resolve()
    database_path = Path(database_path).expanduser().resolve()
    signature = _dump_signature(data_dir)
    if _database_signature(database_path) != signature:
        log.info("building California SQLite database at %s", database_path)
        import_sqlite_database(data_dir, database_path)
    return database_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("database", nargs="?", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    database = args.database or args.data_dir / "capublic.sqlite3"
    if args.force:
        import_sqlite_database(args.data_dir, database)
    else:
        ensure_sqlite_database(args.data_dir, database)
    print(database.expanduser().resolve())


if __name__ == "__main__":
    main()
