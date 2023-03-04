# qabot

Query local csv files or databases with natural language queries powered by
`langchain` and `openai`.

Works on local CSV files:

![](.github/local_csv_query.png)

as well as on real databases:

![](.github/external_db_query.png)


## Quickstart

You need to set the `OPENAI_API_KEY` environment variable to your OpenAI API key, 
which you can get from [here](https://platform.openai.com/account/api-keys).

Install the `qabot` command line tool using pip/poetry:


```bash
$ poetry install qabot
```

Then run the `qabot` command with either files or a database connection string:

### Local CSV file/s

```bash
$ qabot -q "how many passengers survived by gender?" -f data/titanic.csv
🦆 Loading data from files...
Loading data/titanic.csv into table titanic...

Query: how many passengers survived by gender?
Result:
There were 233 female passengers and 109 male passengers who survived.


 🚀 any further questions? [y/n] (y): y

 🚀 Query: what was the largest family who did not survive? 
Query: what was the largest family who did not survive?
Result:
The largest family who did not survive was the Sage family, with 8 members.

 🚀 any further questions? [y/n] (y): n

```

### Existing database

Install any required drivers for your database, e.g. `pip install psycopg2-binary` for postgres.

For example to connect and query directly from the trains database in the [relational dataset repository](https://relational.fit.cvut.cz/dataset/Trains):

```bash
$ pip install mysqlclient

$ qabot -d mysql+mysqldb://guest:relational@relational.fit.cvut.cz:3306/trains -q "what are the unique load shapes of cars, what are the maximum number of cars per train?" 
Query: what are the unique load shapes of cars, what are the maximum number of cars per train?
Result:
The unique load shapes of cars are circle, diamond, hexagon, rectangle, and triangle, and the maximum number of cars per train is 3.

```

Note you can also supply the database connection string via the environment variable
`QABOT_DATABASE_URI`.

#### Limit the tables

You can limit the tables that are queried by passing the `-t` flag. For example, to only query the `cars` table:

```bash
$ export QABOT_DATABASE_URI=mysql+mysqldb://guest:relational@relational.fit.cvut.cz:3306/trains
$ qabot -q "what are the unique load shapes of cars?" -t cars

The unique load shapes of cars are circle, hexagon, triangle, rectangle, and diamond.
```

## See the intermediate steps and database queries

Use the `-v` flag to see the intermediate steps and database queries:

```bash
$ qabot -d mysql+mysqldb://guest:relational@relational.fit.cvut.cz:3306/trains -q "what are the unique load shapes of cars, what are the maximum number of cars per train?" -v
Query: what are the unique load shapes of cars, what are the maximum number of cars per train?
Intermediate Steps: 
  Step 1

    list_tables_sql_db(
      
    )

    Output:
    trains, cars

  Step 2

    schema_sql_db(
      trains, cars
    )

    Output:
    CREATE TABLE trains (
        id INTEGER(11) NOT NULL, 
        direction VARCHAR(4), 
        PRIMARY KEY (id)
    )ENGINE=InnoDB DEFAULT CHARSET=latin1

    SELECT * FROM 'trains' LIMIT 3;
    id  direction
    1   east
    2   east
    3   east


    CREATE TABLE cars (
        id INTEGER(11) NOT NULL, 
        train_id INTEGER(11), 
        `position` INTEGER(11), 
        shape VARCHAR(255), 
        len VARCHAR(255), 
        sides VARCHAR(255), 
        roof VARCHAR(255), 
        wheels INTEGER(11), 
        load_shape VARCHAR(255), 
        load_num INTEGER(11), 
        PRIMARY KEY (id), 
        CONSTRAINT cars_ibfk_1 FOREIGN KEY(train_id) REFERENCES trains (id) ON DELETE CASCADE ON UPDATE CASCADE
    )ENGINE=InnoDB DEFAULT CHARSET=latin1

    SELECT * FROM 'cars' LIMIT 3;
    id  train_id        position        shape   len     sides   roof    wheels  load_shape      load_num
    1   1       1       rectangle       short   not_double      none    2       circle  1
    2   1       2       rectangle       long    not_double      none    3       hexagon 1
    3   1       3       rectangle       short   not_double      peaked  2       triangle        1

  Step 3

    query_sql_db(
      SELECT load_shape, MAX(load_num) FROM cars GROUP BY load_shape
    )

    Output:
    [('circle', 3), ('diamond', 1), ('hexagon', 1), ('rectangle', 3), ('triangle', 3)]


Result:
The unique load shapes of cars are circle, diamond, hexagon, rectangle, and triangle, and the maximum number of cars per train is 3.

```

### Links
- [Python library docs](https://langchain.readthedocs.io)
- [Agent docs to talk to arbitrary apis via OpenAPI/Swagger](https://langchain.readthedocs.io/en/latest/modules/agents/agent_toolkits/openapi.html)
- [Agents/Tools to talk SQL](https://langchain.readthedocs.io/en/latest/modules/agents/agent_toolkits/sql_database.html)
- [Typescript library](https://hwchase17.github.io/langchainjs/docs/overview/)

