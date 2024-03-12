import logging

from qabot.functions.duckdb_query import run_sql_catch_error


def describe_table_or_view(database, table: str , schema=None, catalog=None):
    """
    Show the column names and types of a local database table or view.

    Note if the catalog is not default we don't compute the size of the table.
    """
    logging.debug(f"describe_table_or_view({table}, {schema}, {catalog})")

    # Identify the catalog, schema and table - if not provided
    if catalog is None:
        # Search the system.information_schema.tables for the table
        schema_clause = f" and table_schema='{schema}'" if schema is not None else ""
        table_catalog_query = f"select table_catalog from system.information_schema.tables where table_name='{table}'{schema_clause} limit 1;"
        catalog_row = database.sql(table_catalog_query).fetchone()
        if not catalog_row:
            return f"Table {table} not found in any catalog"
        catalog = catalog_row[0]

    if schema is None:
        schema_query = f"select table_schema from system.information_schema.tables where table_name='{table}' and table_catalog='{catalog}' limit 1;"
        schema_row = database.sql(schema_query).fetchone()
        if schema_row is None:
            return f"Table {table} not found in catalog {catalog}"
        schema = schema_row[0]

    fully_qualified_table = f"{catalog}.{schema}.{table}"
    logging.debug(fully_qualified_table)
    # If the catalog is external, we avoid computing the size of the table
    if catalog == "memory":
        table_count_rows_query = f"select count(*) from {fully_qualified_table};"
        table_size = table_count_rows_query + '\n' + str(database.sql(table_count_rows_query).fetchone()[0])
    else:
        table_size = ""

    table_columns_and_types_query = f"select column_name, data_type from system.information_schema.columns where table_name='{table}' and table_catalog='{catalog}' and table_schema='{schema}';"

    # Get the names of the first 20 columns of the table
    column_name_query = f"select column_name from system.information_schema.columns where table_name='{table}' and table_catalog='{catalog}' and table_schema='{schema}' limit 20;"
    column_name_results = database.sql(column_name_query).fetchall()
    column_names = [f'"{row[0]}"' for row in column_name_results]
    joined_names = ", ".join(column_names)
    table_first_rows_query = f"select {joined_names} from {fully_qualified_table} limit 5;"

    table_description = run_sql_catch_error(database, table_columns_and_types_query)

    table_preview = run_sql_catch_error(database, table_first_rows_query)[:4000]
    return f"{table}\n{table_description}\n\n{table_size}\n{table_first_rows_query}\n{table_preview}"
