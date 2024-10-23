import sqlite3
import csv

conn = sqlite3.connect('assistant.db')
c = conn.cursor()

# Drop the existing users table if it exists
c.execute("DROP TABLE IF EXISTS meetings")

# Drop the existing users table if it exists
c.execute("DROP TABLE IF EXISTS meeting_participants")

def create_tables():
    
    # Create meetings table
    c.execute('''
    CREATE TABLE IF NOT EXISTS meetings (
        meeting_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        description TEXT
    );
    ''')
    

    # Create a new meeting_participants table with user_email
    c.execute("""
        CREATE TABLE meeting_participants (
            meeting_id INTEGER,
            email TEXT,
            PRIMARY KEY (meeting_id, email),
            FOREIGN KEY (meeting_id) REFERENCES meetings (meeting_id),
            FOREIGN KEY (email) REFERENCES users (email)
        )
    """)


def import_data_from_csv(csv_file_path, insert_query):
    try:
        # Open the CSV file and insert each record
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip the header row
            c.executemany(insert_query, reader)
        print(f"Data successfully imported from {csv_file_path}.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

def import_meetings(csv_file_path):
    # SQL query to insert into meetings
    insert_query = "INSERT INTO meetings (meeting_id, title, start_time, end_time) VALUES (?, ?, ?, ?)"
    import_data_from_csv(csv_file_path, insert_query)

def import_meeting_participants(csv_file_path):
    # SQL query to insert into meeting_participants
    insert_query = "INSERT INTO meeting_participants (meeting_id, email) VALUES (?, ?)"
    import_data_from_csv(csv_file_path, insert_query)

create_tables()

# Import meetings data
import_meetings("../input/meetings.csv")

# Import meeting participants data
import_meeting_participants("../input/meeting_participants_v2.csv")


# Commit changes and close the connection
conn.commit()
conn.close()