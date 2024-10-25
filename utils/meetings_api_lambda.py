import os
import pymysql
import sqlite3
import pandas as pd
import logging
import json
import random
from datetime import date
from datetime import datetime, timedelta
from utils.constants import *

def init_logging():
    logging.basicConfig(
        level=logging.INFO,  # You can adjust the level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format='%(asctime)s - %(levelname)s - %(message)s',  # Customize the format
        handlers=[
            logging.StreamHandler()  # To output to the console
            # logging.FileHandler("app.log")  # To output to a file
        ]
    )

is_lambda = "AWS_LAMBDA_FUNCTION_NAME" in os.environ

if is_lambda:
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_name = os.environ.get("DB_NAME")
    connection = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )
    init_logging()

def run_func(func, *args):
    if is_lambda:
        logging.info("lambda connection detected")
        with connection.cursor() as cursor:
            results = func(cursor, *args)
    else:
        connection = sqlite3.connect('assistant.db')
        with connection:
            connection.execute("BEGIN")
            cursor = connection.cursor()
            results = func(cursor, *args)
    if results is None:
        connection.commit()
    return results

def is_iso8601(date_string):
    try:
        datetime.fromisoformat(date_string)
        return True
    except ValueError:
        return False

def get_meetings(cursor, emails, start_day, end_day):
    email_meetings = {}
    for email in emails:
        # Query to fetch meetings within the start_day and end_day for the given email
        cursor.execute("""
            SELECT m.start_time, m.end_time
            FROM meetings m
            JOIN meeting_participants mp ON m.meeting_id = mp.meeting_id
            WHERE mp.email = ?
            AND m.start_time >= ? AND m.end_time <= ?
        """, (email, start_day, end_day))

        # Fetch all meeting time slots for the email within the date range
        meetings = cursor.fetchall()

        # Store the results in the dictionary
        email_meetings[email] = {
            "meetings_timeslots": [{
                "start_time": meeting[0], 
                "end_time": meeting[1]
            } for meeting in meetings]
        }
    return email_meetings

def check_overlapping_meetings(cursor, emails, proposed_start_time, proposed_end_time):
    emails_availabilities = {key : {} for key in emails}
    for email in emails:
        availability = True  # Assume the attendee is available by default

        # Fetch any meetings that overlap with the proposed timeslot
        cursor.execute("""
            SELECT m.start_time, m.end_time
            FROM meetings m
            JOIN meeting_participants mp ON m.meeting_id = mp.meeting_id
            WHERE mp.email = ?
            AND m.start_time <= ? AND m.end_time >= ?
        """, (email, proposed_end_time, proposed_start_time))

        overlapping_meetings = cursor.fetchall()

        # If there are any overlapping meetings, the attendee is unavailable
        if overlapping_meetings:
            availability = False

        # Store availability result for the attendee
        emails_availabilities[email]["availability"] = availability
    return emails_availabilities


def check_availabilities(data):
    emails = data["attendees_by_email"]
    start_day = datetime.fromisoformat(data["start_day"])
    end_day = datetime.fromisoformat(data["end_day"])
    try:
        emails_meetings = run_func(get_meetings, emails, start_day, end_day)

        # If proposed timeslot is provided, check availability
        if "proposed_timeslot_start_time" in data and "proposed_timeslot_end_time" in data:
            proposed_start_time = datetime.fromisoformat(data["proposed_timeslot_start_time"])
            proposed_end_time = datetime.fromisoformat(data["proposed_timeslot_end_time"])

            emails_availabilities = run_func(check_overlapping_meetings, emails, proposed_start_time, proposed_end_time)
            emails_data = {key: {**emails_meetings.get(key), **emails_availabilities.get(key)} for key in set(emails_meetings) | set(emails_availabilities)}
        return emails_data
    except (sqlite3.Error, pymysql.MySQLError) as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        return f"Error while checking availabilities. Tell user to contact administrator if the error persists: {e}"


def get_email_request(cursor, name):
    # Execute the SQL query to find the email by name
    cursor.execute("SELECT email FROM users WHERE LOWER(name) = ?", (name,))
    # Fetch one result
    result = cursor.fetchone()
    return result

def get_email_by_name(name):
    try:
        result = run_func(get_email_request, name)
        return result
    except (sqlite3.Error, pymysql.MySQLError) as e:
        logging.error(f"An error occurred while fetching an email : {e}", exc_info=True)
        return None


def check_attendees(names):
    attendees = {key: None for key in names}
    for name in names:
        attendees[name] = get_email_by_name(name.lower())
    return json.dumps(attendees)


def get_users():
    query = "SELECT * FROM users"
    try:
        if is_lambda:
            return pd.read_sql_query(query, connection)
        else:
            return pd.read_sql_query(query, sqlite3.connect('assistant.db'))
    except (sqlite3.Error, pymysql.MySQLError):
        logging.error(f"Error: {str(e)}", exc_info=True)
        success = False
        description = f"Error while creating the meeting. Tell user to contact administrator if the error persists: {e}"
        return json.dumps({"success": success, "description": description})

def insert_meeting(cursor, title, start_time, end_time, participants):
    # Insert the new meeting using cursor
    cursor.execute("""
        INSERT INTO meetings (title, start_time, end_time)
        VALUES (?, ?, ?)
    """, (title, start_time, end_time))

    # Get the meeting_id of the newly inserted meeting
    meeting_id = cursor.execute("SELECT last_insert_rowid()").fetchone()[0]


    # Insert the participants for the new meeting
    for user_email in participants:
        cursor.execute("""
            INSERT INTO meeting_participants (meeting_id, email)
            VALUES (?, ?)
        """, (meeting_id, user_email))
    return None


def setup_meeting(data):
    title = data["title"]
    start_time = data["start_time"]
    end_time = data["end_time"]
    participants = data["attendees_by_email"]
    try:
        run_func(insert_meeting, title, start_time, end_time, participants)
        success = True
        description = ""
    except (sqlite3.Error, pymysql.MySQLError) as e:
        logging.error(f"Error: {str(e)}", exc_info=True)
        success = False
        description = f"Error while creating the meeting. Tell user to contact administrator if the error persists: {e}"

    return json.dumps({"success": success, "description": description})



def check_availabilities_json(data):
    return(json.dumps(check_availabilities(data)))


# Extracted function to normalize availabilities for a single attendee
def normalize_availabilities_for_attendee(email, meetings_list, days):
    daily_availabilities = {}
    for day in days:
        work_hours = generate_work_hours_for_day(day)
        unavailable_intervals = get_unavailable_intervals(meetings_list["meetings_timeslots"], day)
        available_intervals = subtract_intervals(work_hours, unavailable_intervals)
        daily_availabilities[day.date()] = available_intervals
    return daily_availabilities

# Extracted function to find common intervals between all attendees
def find_common_intervals(normalized_availabilities, days, meeting_duration):
    common_intervals_per_day = {}
    attendee_emails = list(normalized_availabilities.keys())

    for day in days:
        common_intervals = normalized_availabilities[attendee_emails[0]][day.date()]

        for email in attendee_emails[1:]:
            common_intervals = find_overlapping_intervals(common_intervals, normalized_availabilities[email][day.date()], meeting_duration)

        if common_intervals:
            common_intervals_per_day[day.date()] = common_intervals

    return common_intervals_per_day

# Extracted function to generate proposed slots from common intervals
def proposed_slots_generation(common_intervals_per_day, meeting_duration):
    proposed_slots = []
    for day, intervals in common_intervals_per_day.items():
        # Split into meeting slots
        slots = split_into_slots(intervals, meeting_duration)
        if slots:  # If there's any available slot on this day
            proposed_slots.append(random.choice(slots))  # Just propose the first slot of each day
    return proposed_slots

# Main propose_availabilities function with refactored steps
def propose_availabilities(data):
    meetings = check_availabilities(data)
    start_day = datetime.fromisoformat(data["start_day"])
    end_day = datetime.fromisoformat(data["end_day"])
    meeting_duration = data["meeting_duration"]

    # Step 1: Generate all the days between start_day and end_day
    days = generate_days(start_day, end_day)
    
    # Step 2: Compute available intervals for each attendee for each day
    normalized_availabilities = {
        email: normalize_availabilities_for_attendee(email, meetings_list, days)
        for email, meetings_list in meetings.items()
    }

    # Step 3: Find common intervals between all attendees for each day
    common_intervals_per_day = find_common_intervals(normalized_availabilities, days, meeting_duration)

    # Step 4: Generate proposed slots
    proposed_slots = proposed_slots_generation(common_intervals_per_day, meeting_duration)

    return json.dumps({"common_timeslots": proposed_slots})

# Function to generate all days within the range of start_day to end_day
def generate_days(start_day, end_day):
    days = []
    current_day = start_day
    while current_day <= end_day:
        if current_day.weekday() < 5:
            days.append(current_day)
        current_day += timedelta(days=1)
    return days

# Function to create available time slots during work hours for a specific day
def generate_work_hours_for_day(day):
    start_time = datetime(day.year, day.month, day.day, WORK_START, 0)
    end_time = datetime(day.year, day.month, day.day, WORK_END, 0)
    return [{'start_time': start_time, 'end_time': end_time}]

# Adjust meeting times to reflect unavailability
def get_unavailable_intervals(meeting_list, day):
    unavailable_intervals = []
    for meeting in meeting_list:
        if datetime.fromisoformat(meeting['start_time']).date() == day.date():
            unavailable_intervals.append({
                'start_time': datetime.fromisoformat(meeting['start_time']),
                'end_time': datetime.fromisoformat(meeting['end_time'])
            })
    return unavailable_intervals

# Function to subtract unavailable intervals from available work hours
def subtract_intervals(available_intervals, unavailable_intervals):
    free_intervals = []
    for available in available_intervals:
        temp_intervals = [available]
        for unavailable in unavailable_intervals:
            new_intervals = []
            for temp in temp_intervals:
                if unavailable['start_time'] >= temp['end_time'] or unavailable['end_time'] <= temp['start_time']:
                    # No overlap
                    new_intervals.append(temp)
                else:
                    # There's overlap, we need to subtract the overlapping part
                    if unavailable['start_time'] > temp['start_time']:
                        new_intervals.append({
                            'start_time': temp['start_time'],
                            'end_time': unavailable['start_time']
                        })
                    if unavailable['end_time'] < temp['end_time']:
                        new_intervals.append({
                            'start_time': unavailable['end_time'],
                            'end_time': temp['end_time']
                        })
            temp_intervals = new_intervals
        free_intervals.extend(temp_intervals)
    return free_intervals

# Find overlapping intervals between different attendees
def find_overlapping_intervals(intervals1, intervals2, meeting_duration):
    overlaps = []
    for int1 in intervals1:
        for int2 in intervals2:
            overlap_start = max(int1['start_time'], int2['start_time'])
            overlap_end = min(int1['end_time'], int2['end_time'])
            
            if overlap_end - overlap_start >= timedelta(minutes=meeting_duration):
                overlaps.append({'start_time': overlap_start, 'end_time': overlap_end})
    return overlaps

# Avoid lunch time, if possible
def avoid_lunch_time(interval):
    if interval['start_time'].hour < LUNCH_START and interval['end_time'].hour <= LUNCH_START:
        return True  # Before lunch time
    if interval['start_time'].hour >= LUNCH_END:
        return True  # After lunch time
    return False  # During lunch time

# Split longer intervals into smaller chunks
def split_into_slots(intervals, meeting_duration):
    slots = []
    for interval in intervals:
        slot_start = interval['start_time']
        while slot_start + timedelta(minutes=meeting_duration) <= interval['end_time']:
            slot_end = slot_start + timedelta(minutes=meeting_duration)
            if avoid_lunch_time({'start_time': slot_start, 'end_time': slot_end}):
                slots.append({'start_time': slot_start.strftime("%Y-%m-%dT%H:%M:%S"), 'end_time': slot_end.strftime("%Y-%m-%dT%H:%M:%S"), 'weekday': slot_start.strftime("%A")})
            slot_start = slot_end
    return slots


def lambda_handler(event, context):
    data = event["arguments"]
    func_name = event["name"]
    if func_name == "check_attendees":
        return check_attendees(data["attendees_by_name"])
    if func_name == "setup_meeting":
        if not is_iso8601(data["start_time"]) or not is_iso8601(data["end_time"]):
            logging.error("start_time or end_time not provided is ISO Format", exc_info=True)
            return {
                "error" : True,
                "description" : "Please provide me end_time in the ISO 8601 format : YYYY-MM-DDTHH:MM:SS"
            }
        return setup_meeting(data)
    if func_name == "check_availabilities":
        return check_availabilities_json(data)
    if func_name == "propose_availabilities":
        return propose_availabilities(data)
    if func_name == "follow_up_action":
        message = {"role" : "assistant", "content" : data["content"]}
        st.session_state.messages.append(message)
        write_message(message)
        return "{'description' : 'waiting for follow-up action...'}"
    return {
        "error" : True,
        "description" : "unknown function provided. Please provide me one of the actions provided to you.\n"
    }