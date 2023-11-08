from qabot import ask_wikidata


if __name__ == "__main__":
    result = ask_wikidata("How many hospitals are there in New Zealand?")
    print(result)
