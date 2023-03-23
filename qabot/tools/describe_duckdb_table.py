from qabot.duckdb_query import run_sql_catch_error


def describe_table_or_view(database, table):
    table_columns_and_types_query = f"select column_name, data_type from information_schema.columns where table_name='{table}';"
    table_first_rows_query = f"select * from '{table}' limit 3;"
    table_description = run_sql_catch_error(database, table_columns_and_types_query)
    table_preview = run_sql_catch_error(database, table_first_rows_query)[:4000]
    return f"{table}\n{table_description}\n{table_preview}"
