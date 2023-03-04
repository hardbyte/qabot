import os
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError


def uri_validator(x):
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc])
    except:
        return False


def create_duckdb_from_files(files: list[str]):
    # By default, duckdb is fully in-memory - we can provide a path to get
    # persistent storage

    engine = create_engine("duckdb:///:memory:")

    for i, file_path in enumerate(files, 1):

        load_external_data_into_db(engine, file_path)

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

    return engine


def load_external_data_into_db(engine, file_path, allow_view=False):
    # Work out if the filepath is actually a url (e.g. s3://)
    is_url = uri_validator(file_path)
    # Get the file name without extension from the file_path
    table_name, extension = os.path.splitext(os.path.basename(file_path))
    # If the table_name isn't a valid SQL identifier, we'll need to use something else
    try:
        engine.execute(text(f"create table t_{table_name} as select 1;"))
        engine.execute(text(f"drop table t_{table_name};"))
    except ProgrammingError as e:
        table_name = "data"

    # The SQLAgent doesn't appear to see view's just yet, so we'll create a table instead
    use_view = allow_view and is_url
    if is_url:
        engine.execute(text("INSTALL httpfs;"))
        engine.execute(text("LOAD httpfs;"))

    create_statement = f"create {'view' if use_view else 'table'} '{table_name}' as select * from '{file_path}';"
    engine.execute(text(create_statement))

