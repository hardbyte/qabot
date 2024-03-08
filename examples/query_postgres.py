from qabot import ask_database


if __name__ == "__main__":
    result = ask_database("How many product images are there?", "postgresql://postgres:password@localhost:5432/partly", verbose=False)
    print(result)
