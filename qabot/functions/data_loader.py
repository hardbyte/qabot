import os
from typing import Tuple
from urllib.parse import urlparse
import tempfile

import duckdb
from duckdb import ParserException, ProgrammingError
import httpx


def uri_validator(x):
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc])
    except:
        return False


def create_duckdb(duckdb_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    # By default, duckdb is fully in-memory - we can provide a path to get
    # persistent storage

    duckdb_connection = duckdb.connect(duckdb_path)
    try:
        duckdb_connection.sql("INSTALL httpfs;")
        duckdb_connection.sql("LOAD httpfs;")
    except Exception:
        print(
            "Failed to install httpfs extension. Loading remote files will not be supported"
        )

    duckdb_connection.sql(
        "create table if not exists qabot_queries(query VARCHAR, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
    )

    return duckdb_connection


def import_into_duckdb_from_files(
        duckdb_connection: duckdb.DuckDBPyConnection,
        files: list[str],
        dangerously_allow_write_access=False
) -> Tuple[duckdb.DuckDBPyConnection, list[str]]:
    executed_sql = []
    for i, file_path in enumerate(files, 1):
        if file_path.startswith("postgresql://"):
            try:
                duckdb_connection.sql("INSTALL postgres_scanner;")
            except Exception:
                print(
                    "Failed to install postgres_scanner extension. Loading directly from postgresql will not be supported"
                )
                continue
            db_type = "(TYPE postgres, READ_ONLY)" if not dangerously_allow_write_access else "(TYPE postgres)"
            duckdb_connection.execute(f"ATTACH '{file_path}' as postgres_db {db_type};")

            _set_search_path(duckdb_connection)
        elif file_path.endswith('.xlsx'):
            try:
                duckdb_connection.sql("INSTALL spatial;")
                duckdb_connection.sql("LOAD spatial;")
            except Exception:
                print(
                    "Failed to install spatial extension. Loading directly from Excel files will not be supported"
                )
                continue
            # use the filename as the table name
            table_name, _ = os.path.splitext(os.path.basename(file_path))
            # remove any non-alphanumeric characters
            new_table_name = "".join([c for c in table_name if c.isalnum()])
            duckdb_connection.execute(f"CREATE TABLE {new_table_name} AS select * from st_read('{file_path}');")
            _set_search_path(duckdb_connection)
        elif file_path.endswith(".sqlite"):
            try:
                duckdb_connection.sql("INSTALL sqlite;")
                duckdb_connection.sql("LOAD sqlite;")
            except Exception:
                print(
                    "Failed to install sqlite extension. Loading directly from sqlite will not be supported"
                )
                continue
            #duckdb_connection.execute(f"CALL sqlite_attach('{file_path}')")
            duckdb_connection.execute(f"ATTACH '{file_path}' as sqlite_db (TYPE SQLITE);")
            _set_search_path(duckdb_connection)
        else:
            executed_sql.append(
                load_external_data_into_db(duckdb_connection, file_path)
            )

    return duckdb_connection, executed_sql


def _set_search_path(duckdb_connection: duckdb.DuckDBPyConnection):
    db_names = [x[0] for x in duckdb_connection.sql(f"SELECT database_name FROM duckdb_databases() where internal = false;").fetchall()]
    query = f"set search_path = '{','.join(db_names)}';"
    duckdb_connection.execute(query)

def load_external_data_into_db(
    conn: duckdb.DuckDBPyConnection, file_path, allow_view=True
):
    # Work out if the filepath is actually a url (e.g. s3://)
    is_url = uri_validator(file_path)
    # Get the file name without extension from the file_path
    table_name, extension = os.path.splitext(os.path.basename(file_path))
    # If the table_name isn't a valid SQL identifier, we'll need to use something else

    table_name = (
        table_name.replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )

    try:
        conn.sql(f"create table t_{table_name} as select 1;")
        conn.sql(f"drop table t_{table_name};")
    except (ParserException, ProgrammingError):
        table_name = "data"

    # try to create a view then fallback to a table if it fails
    use_view = allow_view and is_url
    try:
        create_statement = f"create {'view' if use_view else 'table'} '{table_name}' as select * from '{file_path}';"
        conn.sql(create_statement)
    except duckdb.IOException:
        # This can occur if the server doesn't send Content-Length headers
        # We can work around this by downloading the data locally and then
        # loading it from there. We assume CSV files for now
        if is_url:
            with tempfile.NamedTemporaryFile(
                mode="w+b", suffix=".csv", delete=False
            ) as f:
                with httpx.stream("GET", file_path) as r:
                    for chunk in r.iter_bytes():
                        if chunk:
                            f.write(chunk)
                    f.flush()

                create_statement = f"create table '{table_name}' as select * from read_csv_auto('{f.name}');"

        conn.sql(create_statement)

    return create_statement
