import duckdb


def run_sql_catch_error(conn, sql: str):
    # Remove any backtics from the string
    sql = sql.replace("`", "")

    try:

        output = conn.sql(sql)
        if output is None:
            rendered_output = "No output"
        else:
            rendered_output = '\n' + str(output)
        return rendered_output
    except duckdb.ProgrammingError as e:
        return str(e)
    except duckdb.Error as e:
        return str(e)
    # except Exception as e:
    #     return str(e)