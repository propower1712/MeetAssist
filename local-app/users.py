import sqlite3
import csv

# Connect to the SQLite database
conn = sqlite3.connect('assistant.db')
c = conn.cursor()

# Drop the existing users table if it exists
c.execute("DROP TABLE IF EXISTS users")

# Create Users table
c.execute('''
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
)
''')


def import_users_from_csv(csv_file_path):
    # Open the CSV file
    with open(csv_file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Insert each user into the users table
            c.execute("INSERT INTO users (name, email) VALUES (?, ?)", (row['name'], row['email']))


# Call the function with the path to your CSV file
import_users_from_csv('../input/users.csv')


# Commit changes and close the connection
conn.commit()
conn.close()