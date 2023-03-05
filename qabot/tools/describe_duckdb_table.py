from qabot.duckdb_query import run_sql_catch_error


def describe_table_or_view(database, table):
    statement = f"describe {table};"
    table_description = run_sql_catch_error(database, statement)
    return f"{table}\n{table_description}"
