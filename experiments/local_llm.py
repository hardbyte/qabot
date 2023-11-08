from transformers import T5Tokenizer, T5ForConditionalGeneration


# transformers.logging.set_verbosity_info()

tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-large")

input_text = """You are an agent designed to interact with a SQL database.

Given an input question, create a syntactically correct query to run, then look at the results of the
query and return the answer.

Assume the relevant table 'titanic' has the following columns:
┌─────────────┬─────────────┬
│ column_name │ column_type │
├─────────────┼─────────────┼
│ PassengerId │ BIGINT      │
│ Survived    │ BIGINT      │
│ Pclass      │ BIGINT      │
│ Name        │ VARCHAR     │
│ Sex         │ VARCHAR     │
│ Age         │ DOUBLE      │
│ SibSp       │ BIGINT      │
│ Parch       │ BIGINT      │
│ Ticket      │ VARCHAR     │
│ Fare        │ DOUBLE      │
│ Cabin       │ VARCHAR     │
│ Embarked    │ VARCHAR     │
├─────────────┴─────────────┴

Begin!
Question: how many passengers survived by gender?
SQL Query: 
"""
input_ids = tokenizer(input_text, return_tensors="pt").input_ids.to("cuda")
model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-large").to("cuda")
outputs = model.generate(input_ids, max_length=512)
print(tokenizer.decode(outputs[0]))
