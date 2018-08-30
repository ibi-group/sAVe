import json
import sqlite3


# Adds user, give username and password. Should just work, even if username
# is taken.
def add_user(username, password):
    connection = sqlite3.connect('users.db')
    with connection:
        connection.execute('''CREATE TABLE IF NOT EXISTS users(
                                username TEXT DEFAULT NULL,
                                password TEXT DEFAULT NULL,
                                ada INTEGER DEFAULT 0,
                                student INTEGER DEFAULT 0,
                                senior INTEGER DEFAULT 0,
                                income REAL DEFAULT 0,
                                id INTEGER PRIMARY KEY AUTOINCREMENT)''')
        # If username exists already.
        if (
            connection.execute(
                '''
                SELECT * FROM users WHERE username = ?
                ''', (username,)
            ).fetchone()
        ):
            return False
        connection.execute(
            '''
            INSERT INTO users (username, password) VALUES (?,?)
            ''', (username, password,)
        )
    return True


# Checks if password matches username. Currently in plaintext, so please fix.
def verify_user(username, password):
    connection = sqlite3.connect('users.db')
    with connection:
        connection.execute(
            '''CREATE TABLE IF NOT EXISTS users(
                    username TEXT DEFAULT NULL,
                    password TEXT DEFAULT NULL,
                    ada INTEGER DEFAULT 0,
                    student INTEGER DEFAULT 0,
                    senior INTEGER DEFAULT 0,
                    income REAL DEFAULT 0,
                    id INTEGER PRIMARY KEY AUTOINCREMENT)'''
        )
        password_check = connection.execute(
            '''
            SELECT password FROM users WHERE username = ?
            ''', (username,)
        ).fetchone()
    if (not password_check):
        return False
    return (password_check[0] == password)


# Svaes user preferences from settings page.
def save_preference(user_id, preferences):
    # Unify the dictionary.
    input_dictionary = {**dict(user_id=user_id), **preferences}
    connection = sqlite3.connect('users.db')
    with connection:
        connection.execute('''UPDATE users SET
                                ada = :ada,
                                student = :student,
                                senior = :senior,
                                income = :income
                                WHERE
                                    id = :user_id''', input_dictionary)
    return True


# Get the user id given username.
def get_user_id(username):
    connection = sqlite3.connect('users.db')
    with connection:
        return connection.execute(
            '''
            SELECT id FROM users WHERE username = ?
            ''', (username,)
        ).fetchone()


# Get a dictionary of preferences.
def get_preference(user_id):
    connection = sqlite3.connect('users.db')
    connection.row_factory = sqlite3.Row
    with connection:
        preferences = connection.execute(
            '''
            SELECT ada, student, senior, income FROM users WHERE id = ?
            ''', (user_id,)
        ).fetchone()
    return preferences


# Get sums of preferences.
def get_all_preferences():
    connection = sqlite3.connect('users.db')
    connection.row_factory = sqlite3.Row
    with connection:
        count_fetch = connection.execute('''SELECT
                                            SUM(ada) as ada,
                                            SUM(student) as student,
                                            SUM(senior) as senior
                                            FROM users''').fetchone()
        if (not count_fetch):
            return False
        count_dict = dict(count_fetch)
        count = connection.execute(
            '''
            SELECT COUNT(username) FROM users
            '''
        ).fetchone()
        if (count):
            count_dict["Total"] = count[0]
        return count_dict
