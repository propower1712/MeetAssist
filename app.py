import streamlit as st
import numpy as np
import boto3
import json
import xml.etree.ElementTree as ET
from datetime import date
from datetime import datetime, timedelta
import pandas as pd
import sqlite3

WORK_START = 8  # 8 AM
WORK_END = 18   # 6 PM
LUNCH_START = 12
LUNCH_END = 14

weekdays = {0 : "Monday", 1 : "Tuesday", 2 : "Wednesday", 3 : "Thursday", 4 : "Friday", 5 : "Saturday", 6 : "Sunday"}

def get_users():
    query = "SELECT * FROM users"
    return pd.read_sql_query(query, conn)

def trim_string(answer):
    # Find the positions of the tags
    pos_employee = answer.find("</employee>") + len("</employee>")
    pos_lambda = answer.find("</lambda>") + len("</lambda>")

    # Determine the minimum position ignoring not found
    positions = [pos for pos in [pos_employee, pos_lambda] if pos > len("</employee>")]
    if positions:
        min_pos = min(positions)
        return answer[:min_pos]
    else:
        return answer  # Return original if none of the tags are found

def is_employee(text):
    # Parse the text
    root = ET.fromstring(text)
    if root.tag == "employee":
        return True
    else:
        return False

def get_root_text(text):
    # Parse the text
    print(text)
    root = ET.fromstring(text)
    return root.text

    
def is_iso8601(date_string):
    try:
        datetime.fromisoformat(date_string)
        return True
    except ValueError:
        return False

def send_to_llm(text):
    body = json.dumps({
        "prompt": st.session_state.prompt + repeat_instructions + "[/INST]",
        "max_tokens": 1024,
        "top_p": 1,
        "temperature": 0
    })
    resp = client.invoke_model(
        body=body,
        modelId=modelId,
        accept="application/json",
        contentType="application/json"
    )
    outputs = json.loads(resp.get("body").read())['outputs']
    print("outputs : \n")
    print(outputs)
    return trim_string(outputs[0]['text'])

def generate_lambda_answer(prompt):
    return "Lambda : {}".format(prompt)

def get_email_by_name(name):
    try:
        # Execute the SQL query to find the email by name
        cursor.execute("SELECT email FROM users WHERE name = ?", (name,))
        # Fetch one result
        result = cursor.fetchone()
        return result
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None


def check_users(names):
    attendees = {key: None for key in names}
    for name in names:
        attendees[name] = get_email_by_name(name)
    json_attendees = json.dumps(attendees)
    return generate_lambda_answer("{}. Check with employee if this information is correct. ask employee to select only one email for each name if the system returned more than one email for a single name.".format(json_attendees))

def setup_meeting(data):
    title = data["title"]
    start_time = data["start_time"]
    end_time = data["end_time"]
    participants = data["attendees"]
    try:
        # Insert the new meeting
        cursor.execute("""
            INSERT INTO meetings (title, start_time, end_time)
            VALUES (?, ?, ?)
        """, (title, start_time, end_time))
        
        # Get the meeting_id of the newly inserted meeting
        meeting_id = cursor.lastrowid
        
        # Insert the participants for the new meeting
        for user_email in participants:
            cursor.execute("""
                INSERT INTO meeting_participants (meeting_id, email)
                VALUES (?, ?)
            """, (meeting_id, user_email))
        
        # Commit the transaction
        conn.commit()
    except Exception as e:
        return generate_lambda_answer(f"Error while creating the meeting. Tell employee to contact administrator if the error persist :  {e}")
    return generate_lambda_answer("Meeting Created Successfully")

def check_availabilities(data):
    email_meetings = {}
    emails = data["attendees_by_email"]
    # Iterate over each email and fetch associated meeting time slots
    try:
        for email in emails:
            cursor.execute("""
                SELECT m.start_time, m.end_time
                FROM meetings m
                JOIN meeting_participants mp ON m.meeting_id = mp.meeting_id
                WHERE mp.email = ?
            """, (email,))
        
            # Fetch all meeting time slots for the email
            meetings = cursor.fetchall()

            # Store the results in the dictionary
            email_meetings[email] = {"meetings_timeslots" : [{
                                            "start_time": meeting[0], 
                                            "end_time": meeting[1]
                                            } for meeting in meetings
                                        ]
                                    }
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return generate_lambda_answer(f"Error while checking availabilities. Tell employee to contact administrator if the error persist :  {e}")
    if "proposed_timeslot" in data:
        proposed_start_time = datetime.fromisoformat(data["proposed_timeslot"]["start_time"])
        proposed_end_time = datetime.fromisoformat(data["proposed_timeslot"]["end_time"])
        for email in emails:
            availability = True
            for meeting in email_meetings[email]["meetings_timeslots"]:
                start_time = datetime.fromisoformat(meeting["start_time"])
                end_time = datetime.fromisoformat(meeting["end_time"])
                if start_time <= proposed_end_time and proposed_start_time <= end_time:
                    availability = False
                else: 
                    availability = True
            email_meetings[email]["availability"] = availability

    return email_meetings


def get_users():
    query = "SELECT * FROM users"
    return pd.read_sql_query(query, conn)


def find_common_availabilities(data):
    """
    Function to find common availabilities for all attendees based on existing meetings.
    
    :param meetings: Dictionary where the key is an email and the value is a list of meetings (each meeting is a dict with 'start_time' and 'end_time').
    :param start_day: Starting day (datetime object).
    :param end_day: Ending day (datetime object).
    :param meeting_duration: Duration of the meeting in hours (float or int).
    :return: List of time intervals where the maximum number of attendees are available for the meeting.
    """

    # Generate all days within the range of start_day to end_day
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
    def find_overlapping_intervals(intervals1, intervals2):
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

    # Split longer intervals into smaller 2-hour chunks
    def split_into_2_hour_slots(intervals, meeting_duration):
        two_hour_slots = []
        for interval in intervals:
            slot_start = interval['start_time']
            while slot_start + timedelta(minutes=meeting_duration) <= interval['end_time']:
                slot_end = slot_start + timedelta(minutes=meeting_duration)
                if avoid_lunch_time({'start_time': slot_start, 'end_time': slot_end}):
                    two_hour_slots.append({'start_time': slot_start, 'end_time': slot_end, 'weekday': weekdays[slot_start.weekday()]})
                slot_start = slot_end
        return two_hour_slots

    meetings = check_availabilities(data)
    start_day = datetime.fromisoformat(data["start_day"])
    end_day = datetime.fromisoformat(data["end_day"])
    meeting_duration = data["meeting_duration"]

    # Step 1: Generate all the days between start_day and end_day
    days = generate_days(start_day, end_day)
    
    # Step 2: Compute available intervals for each attendee for each day
    normalized_availabilities = {}
    for email, meetings_list in meetings.items():
        daily_availabilities = {}
        for day in days:
            # Step 2.1: Get work hours for the day (8 AM - 6 PM)
            work_hours = generate_work_hours_for_day(day)
                
            # Step 2.2: Subtract unavailable intervals (meetings) from work hours
            unavailable_intervals = get_unavailable_intervals(meetings_list["meetings_timeslots"], day)
            available_intervals = subtract_intervals(work_hours, unavailable_intervals)
            
            daily_availabilities[day.date()] = available_intervals
        
        normalized_availabilities[email] = daily_availabilities
    
    # Step 3: Find common intervals between all attendees for each day
    common_intervals_per_day = {}
    attendee_emails = list(normalized_availabilities.keys())
    
    for day in days:
        common_intervals = normalized_availabilities[attendee_emails[0]][day.date()]
        
        for email in attendee_emails[1:]:
            common_intervals = find_overlapping_intervals(common_intervals, normalized_availabilities[email][day.date()])
        
        # Split into 2-hour slots
        common_intervals = split_into_2_hour_slots(common_intervals, meeting_duration)
        
        if common_intervals:
            common_intervals_per_day[day.date()] = common_intervals

    # Step 4: Prioritize proposing slots across different days
    proposed_slots = []
    for day, intervals in common_intervals_per_day.items():
        if intervals:  # If there's any available slot on this day
            proposed_slots.append(intervals[0])  # Just propose the first slot of each day

    return generate_lambda_answer("Proposed Timeslots : {}".format(proposed_slots))


def analyze_lambda_json(json_string):
    data = json.loads(json_string)
    if "action" not in data:
        print("action not found")
        return generate_lambda_answer("Action not provided. Please provide me one of the following actions {}.\n".format(allowed_actions))
    action = data["action"]
    if action == "check_attendees":
        if("attendees_by_name" not in data):
            print("attendees_by_name not found")
            return generate_lambda_answer("you didn't provide either attendees_by_name or attendees_by_email. Please provide it even with empty list.")
        if not isinstance(data["attendees_by_name"], list):
            print("attendees_by_name is not a list.")
            return generate_lambda_answer("attendees_by_name is not a list. Please provide it in a list format.")
        return check_users(data["attendees_by_name"])
    if action == "setup_meeting":
        if "attendees" not in data:
            print("attendees is not provided")
            return generate_lambda_answer("Please provide me attendees in list format")
        if "title" not in data:
            print("title is not provided")
            return generate_lambda_answer("Please provide me the title of the meeting")
        if not isinstance(data["attendees"], list):
            print("attendees is not a list")
            return generate_lambda_answer("Please provide me attendees in form of a list of emails")
        if "start_time" not in data:
            print("start_time not provided")
            return generate_lambda_answer("Please provide me start_time in the ISO 8601 format : YYYY-MM-DDTHH:MM:SS")
        if "end_time" not in data:
            print("end_time not provided")
            return generate_lambda_answer("Please provide me end_time in the ISO 8601 format : YYYY-MM-DDTHH:MM:SS")
        if not is_iso8601(data["start_time"]):
            print("start_time not provided is ISO Format")
            return generate_lambda_answer("Please provide me start_time in the ISO 8601 format : YYYY-MM-DDTHH:MM:SS")
        if not is_iso8601(data["end_time"]):
            print("end_time not provided is ISO Format")
            return generate_lambda_answer("Please provide me end_time in the ISO 8601 format : YYYY-MM-DDTHH:MM:SS")
        return setup_meeting(data)
    if action in ["check_availabilities", "propose_availabilities"]:
        if "attendees_by_email" not in data:
            print("attendees emails is not provided")
            return generate_lambda_answer("Please provide me list of emails attendees_by_email")
        if action == "check_availabilities":
            return check_availabilities(data)
        else:
            return find_common_availabilities(data)
    return "Lambda : unknown action provided. Please provide me one of the following actions {}.\n".format(allowed_actions)


def get_llm_answer(user_prompt):
    lambda_callbacks = 0
    st.session_state.prompt += "Employee : " + user_prompt + "\n"
    llm_answer = send_to_llm(st.session_state.prompt)
    st.session_state.prompt += llm_answer + "\n"
    root_text = get_root_text(llm_answer)
    while (not is_employee(llm_answer)) & (lambda_callbacks < 3):
        st.session_state.lambda_json_code =  root_text
        st.session_state.prompt += "{}\n".format(analyze_lambda_json(root_text))
        llm_answer = send_to_llm(st.session_state.prompt)
        st.session_state.prompt += llm_answer + "\n"
        root_text = get_root_text(llm_answer)
        lambda_callbacks += 1
    return root_text

# Connect to the SQLite database
conn = sqlite3.connect('assistant.db')
cursor = conn.cursor()

today = date.today()
# Create a session with a specific region
session = boto3.Session(region_name='us-east-1')
client = session.client("bedrock-runtime")
modelId = "mistral.mistral-large-2402-v1:0"
accept = "application/json"
contentType = "application/json"

allowed_actions = ["check_attendees", "setup_meeting", "check_availabilities", "propose_availabilities"]


if 'lambda_json_code' not in st.session_state:
        st.session_state.lambda_json_code =  {
        "message": "Json interactions will show up here"
    }

st.title("Json interactions :")

st.json(st.session_state.lambda_json_code)

st.title("List of Users :")



st.dataframe(get_users())

st.title("Meeting Assistant")

if "prompt" not in st.session_state:
    # Open the text file in read mode
    with open('initial_prompt.txt', 'r') as file:
        # Read the entire content of the file into a string variable
        st.session_state.prompt = file.read() + "\n"

print(st.session_state.prompt)  

repeat_instructions = "The assistant should generate answers inside <employee></employee> or <lambda></lambda> and nothing outside. You should not answer instead of employees or lambda. You should not answer employee and lambda at the same time. Confirm the meeting details with employee when available then send them to lambda."


# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello ! How can I help you today ?"}]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"].replace("\n", "\n\n"))


# React to user input
if user_prompt := st.chat_input("What is up?"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    response = get_llm_answer(user_prompt)
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()