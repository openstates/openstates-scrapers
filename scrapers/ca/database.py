import os
from pathlib import Path


MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")


def get_database_url(options):
    """Resolve CA's database without coupling the scraper to one backend."""
    database_url = options.pop("database_url", None) or os.environ.get(
        "CA_DATABASE_URL"
    )
    data_dir = options.pop("data_dir", None) or os.environ.get("CA_DATA_DIR")
    sqlite_path = options.pop("sqlite_path", None) or os.environ.get("CA_SQLITE_PATH")

    host = options.pop("host", MYSQL_HOST)
    user = options.pop("user", MYSQL_USER)
    password = options.pop("pw", MYSQL_PASSWORD)
    database = options.pop("db", "capublic")

    if database_url:
        return database_url

    if data_dir:
        from .sqlite_import import ensure_sqlite_database

        data_dir = Path(data_dir).expanduser().resolve()
        database_path = (
            Path(sqlite_path).expanduser().resolve()
            if sqlite_path
            else data_dir / "capublic.sqlite3"
        )
        ensure_sqlite_database(data_dir, database_path)
        return f"sqlite:///{database_path}"

    if (user is not None) and (password is not None):
        connection = f"mysql://{user}:{password}@"
    else:
        connection = "mysql://"
    return f"{connection}{host}/{database}?charset=utf8"
