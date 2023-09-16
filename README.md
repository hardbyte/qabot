# qabot

Query local or remote files with natural language queries powered by
OpenAI's `gpt` and `duckdb` 🦆.

Can query Wikidata and local files.

## Command Line Usage

```bash
$ EXPORT OPENAI_API_KEY=sk-...
$ EXPORT QABOT_MODEL_NAME=gpt-4
$ qabot -w -q "How many Hospitals are there located in Beijing"
Query: How many Hospitals are there located in Beijing
There are 39 hospitals located in Beijing.
Total tokens 1749 approximate cost in USD: 0.05562
```

## Python Usage

```python
from qabot import ask_wikidata, ask_file

print(ask_wikidata("How many hospitals are there in New Zealand?"))
print(ask_file("How many men were aboard the titanic?", 'data/titanic.csv'))
```

Output:
```text
There are 54 hospitals in New Zealand.
There were 577 male passengers on the Titanic.
```


## Features

Works on local CSV files:

![](.github/local_csv_query.png)

remote CSV files:

```
$ qabot \
    -f https://www.stats.govt.nz/assets/Uploads/Environmental-economic-accounts/Environmental-economic-accounts-data-to-2020/renewable-energy-stock-account-2007-2020-csv.csv \
    -q "How many Gigawatt hours of generation was there for Solar resources in 2015 through to 2020?"
```


Even on (public) data stored in S3:

![](.github/external_s3_data.png)

You can even load data from disk via the natural language query, but that doesn't always work...


> "Load the file 'data/titanic_survival.parquet' into a table called 'raw_passengers'. Create a view of the raw passengers table for just the male passengers. What was the average fare for surviving male passengers?"


After a bit of back and forth with the model, it gets there:

> The average fare for surviving male passengers from the 'male_passengers' view where the passenger survived is 40.82. I ran the query: SELECT AVG(Fare) FROM male_passengers WHERE Survived = 1 AND Sex = 'male';
The average fare for surviving male passengers is 40.82.


## Quickstart

You need to set the `OPENAI_API_KEY` environment variable to your OpenAI API key, 
which you can get from [here](https://platform.openai.com/account/api-keys).

Install the `qabot` command line tool using pip/poetry:


```bash
$ pip install qabot
```

Then run the `qabot` command with either local files (`-f my-file.csv`) or `-w` to query wikidata.


## Examples

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


## Query WikiData

Use the `-w` flag to query wikidata. For best results use the `gpt-4` model.
```bash
$ EXPORT QABOT_MODEL_NAME=gpt-4
$ qabot -w -q "How many Hospitals are there located in Beijing"
```

## Intermediate steps and database queries

Use the `-v` flag to see the intermediate steps and database queries.
Sometimes it takes a long route to get to the answer, but it's interesting to see how it gets there.

```
qabot -f data/titanic.csv -q "how many passengers survived by gender?" -v
```

## Data accessed via http/s3

Use the `-f <url>` flag to load data from a url, e.g. a csv file on s3:

```bash
$ qabot -f s3://covid19-lake/enigma-jhu-timeseries/csv/jhu_csse_covid_19_timeseries_merged.csv -q "how many confirmed cases of covid are there?" -v
🦆 Loading data from files...
create table jhu_csse_covid_19_timeseries_merged as select * from 's3://covid19-lake/enigma-jhu-timeseries/csv/jhu_csse_covid_19_timeseries_merged.csv';

Result:
264308334 confirmed cases
```



## Ideas

- streaming mode to output results as they come in
- token limits
- Supervisor agent - assess whether a query is "safe" to run, could ask for user confirmation to run anything that gets flagged.
- Often we can zero-shot the question and get a single query out - perhaps we try this before the MKL chain
- test each zeroshot agent individually
- Generate and pass back assumptions made to the user
- Add an optional "clarify" tool to the chain that asks the user to clarify the question
- Create a query checker tool that checks if the query looks valid and/or safe
- Inject AWS credentials into duckdb so we can access private resources in S3

- Automatic publishing to pypi. Look at https://blog.pypi.org/posts/2023-04-20-introducing-trusted-publishers/