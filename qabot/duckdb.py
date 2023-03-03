import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


def create_duckdb_from_files(files: list[str]):
    # By default, duckdb is fully in-memory - we can provide a path to get
    # persistent storage

    engine = create_engine("duckdb:///:memory:")

    for file_path in files:

        # Get the file name without extension from the file_path
        table_name, extension = os.path.splitext(os.path.basename(file_path))
        print(f"Loading {file_path} into table {table_name}...")

        if extension == ".json":
            engine.execute(text(f"create table {table_name} as select * from read_json_auto('{file_path}');"))
        else:
            # this works, but auto-detects the column types, which might throw away information
            engine.execute(text(f"create table {table_name} as select * from '{file_path}';"))

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

