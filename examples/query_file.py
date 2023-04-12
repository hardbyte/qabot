from qabot import ask_file


if __name__ == '__main__':
    result = ask_file("How many men were aboard the titanic?", 'data/titanic.csv')
    print(result)
