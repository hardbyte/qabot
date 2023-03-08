from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain import VectorDBQA
from langchain.document_loaders import WebBaseLoader

"""
Notes:

- requires torch etc for embedding. Requires installing the optional `embedding` group of dependencies.
- currently just loads one html page, could do something more like ReadTheDocsLoader
  to load all.

"""

def get_duckdb_docs_chain(llm):
    embeddings = OpenAIEmbeddings()
    loader = WebBaseLoader("https://duckdb.org/docs/sql/introduction")
    docs = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(docs)
    docdb = Chroma.from_documents(texts, embeddings, collection_name="duckdb")
    return VectorDBQA.from_chain_type(llm=llm, chain_type="stuff", vectorstore=docdb)

