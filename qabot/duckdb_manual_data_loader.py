import os
from typing import Tuple
from urllib.parse import urlparse
import duckdb
from duckdb import ParserException, ProgrammingError


def uri_validator(x):
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc])
    except:
        return False


def create_duckdb(duckdb_path: str = ':memory:') -> duckdb.DuckDBPyConnection:
    # By default, duckdb is fully in-memory - we can provide a path to get
    # persistent storage

    duckdb_connection = duckdb.connect(duckdb_path)
    try:
        duckdb_connection.sql("INSTALL httpfs;")
        duckdb_connection.sql("LOAD httpfs;")
    except Exception:
        print("Failed to install httpfs extension. Only loading from local files will be supported")

    duckdb_connection.sql("create table if not exists qabot_queries(query VARCHAR, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")

    return duckdb_connection


def import_into_duckdb_from_files(duckdb_connection: duckdb.DuckDBPyConnection, files: list[str]) -> Tuple[duckdb.DuckDBPyConnection, list[str]]:

    executed_sql = []
    for i, file_path in enumerate(files, 1):

        executed_sql.append(load_external_data_into_db(duckdb_connection, file_path))

        # Alternative is to allow user to pass in column types:
        # conn.sql(f"""
        # create table {table_name} as (
        #     select * from read_csv_auto(
        #         '%s',
        #         delim='|',
        #         header=True,
        #         --types={'phone': 'VARCHAR'}
        #     )
        # )
        # """ % file_path)

    return duckdb_connection, executed_sql


def load_external_data_into_db(conn: duckdb.DuckDBPyConnection, file_path, allow_view=True):
    # Work out if the filepath is actually a url (e.g. s3://)
    is_url = uri_validator(file_path)
    # Get the file name without extension from the file_path
    table_name, extension = os.path.splitext(os.path.basename(file_path))
    # If the table_name isn't a valid SQL identifier, we'll need to use something else

    table_name = table_name.replace("-", "_").replace(".", "_").replace(" ", "_").replace('/', '_')

    try:
        conn.sql(f"create table t_{table_name} as select 1;")
        conn.sql(f"drop table t_{table_name};")
    except (ParserException, ProgrammingError) as e:
        table_name = "data"

    # The SQLAgent doesn't appear to see view's just yet, so we'll create a table instead
    use_view = allow_view and is_url

    create_statement = f"create {'view' if use_view else 'table'} '{table_name}' as select * from '{file_path}';"

    conn.sql(create_statement)

    return create_statement
