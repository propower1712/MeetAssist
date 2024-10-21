import streamlit as st
import numpy as np
from openai import OpenAI
import json
import xml.etree.ElementTree as ET
from datetime import date
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
import re
import traceback

tools = [
    {
        "type" : "function",
        "function" : {
            "name" : "check_attendees",
            "description": "Verify attendees in the database using by name. If attendees' emails are provided, skip this check. Check correctness of returned emails using this function before asking the user for emails if not found.",
            "parameters" : {
                "type" : "object",
                "properties" : {
                    "attendees_by_name" : {
                        "type" : "array",
                        "items" : {
                            "type" : "string"
                        },
                        "description" : "Provide list of names here. For example : ['Eva Martin', 'Lucas Henry', 'Adonas Ringu']"
                    }
                },
                "required": ["attendees_by_name"]
            }
        }
    },
    {
        "type" : "function",
        "function" : {
            "name" : "check_availabilities",
            "description": "Use this function to check availabilities of attendees when the user gives you a timeslot. You need first to get their emails. Interpret an empty list as result of function as full availability. Please always remember that this function returns list of meetings, the availabilities are outside those timeslots.",
            "parameters" : {
                "type" : "object",
                "properties" : {
                    "attendees_by_email" : {
                        "type" : "array",
                        "items" : {
                            "type" : "string"
                        },
                        "description" : "Provide list of emails to get their availabilities"
                    },
                    "proposed_timeslot_start_time" : {
                        "type" : "string",
                        "description" : "Proposed start time for the meeting. If the user has some preference for a specific timeslot, this can be helpful to get the information if the attendees are available during that timeslot. Provide it in the following format : %Y-%m-%dT%H:%M:%S."
                    },
                    "proposed_timeslot_end_time" : {
                        "type" : "string",
                        "description" : "Proposed end time for the meeting. Provide it in the following format : %Y-%m-%dT%H:%M:%S."
                    },
                    "start_day": {
                        "type" : "string",
                        "description" : "The first day where to check availabilities. Always default it to today if not provided by the user. Provide it in the following format : %Y-%m-%dT%H:%M:%S."
                    },
                    "end_day": {
                        "type" : "string",
                        "description" : "The last day where to check availabilities. Always default it to one week after the start_day if not provided by the user. Provide it in the following format : %Y-%m-%dT%H:%M:%S."
                    }
                },
                "required" : ["attendees_by_email", "start_day", "end_day"]
            }
        }
    },
    {
        "type" : "function",
        "function" : {
            "name" : "propose_availabilities",
            "description" : "If no preferred timeslot or attendees are unavailable, ask for preferred timeframe (e.g., 'next week'), and duration (e.g., '1 hour') and this function will propose some available timeslots for you.",
            "parameters" : {
                "type" : "object",
                "properties" : {
                    "attendees_by_email" : {
                        "type" : "array",
                        "items" : {
                            "type" : "string"
                        },
                        "description" : "list of emails' attendees to check their availabilities."
                    },
                    "start_day" : {
                        "type" : "string",
                        "description" : "this is the first day to check availabilities. Provide it in the following format : %Y-%m-%dT%H:%M:%S"
                    },
                    "end_day" : {
                        "type" : "string",
                        "description" : "this is the last day calendar to check availabilities. Provide it in the following format : %Y-%m-%dT%H:%M:%S"
                    },
                    "meeting_duration" : {
                        "type" : "integer",
                        "description" : "the meeting duration in minutes."
                    }
                },
                "required" : ["attendees_by_email", "start_day", "end_day", "meeting_duration"]
            }
        }
    },
    {
        "type" : "function",
        "function" : {
            "name" : "setup_meeting",
            "description" : "Set up the meeting by calling this function. You need to gather all the required information before you proceed. The return result will confirm the meeting creation.",
            "parameters" : {
                "type" : "object",
                "properties" : {
                    "attendees_by_email" : {
                        "type" : "array",
                        "items" : {
                            "type" : "string"
                        },
                        "description" : "list of emails' attendees to set up the meeting."
                    },
                    "start_time" : {
                        "type" : "string",
                        "description" : "The start time of the meeting"
                    },
                    "end_time" : {
                        "type" : "string",
                        "description" : "The end time of the meeting"
                    },
                    "title" : {
                        "type" : "string",
                        "title" : "the title of the meeting"
                    }
                },
                "required" : ["attendees_by_email", "start_time", "end_time", "title"]
            }
        }
    },
    {
        "type" : "function",
        "function" : {
            "name" : "follow_up_action",
            "description" : "Use this function when you need to send to the user a message without requiring any input from him. For example, you should not tell the user to wait without doing a follow up action. This would make him wait for nothing.",
            "parameters" : {
                "type" : "object",
                "properties" : {
                    "content" : {
                        "type" : "string",
                        "description" : "The reply to the user while waiting for a follow-up message."
                    }
                },
                "required" : ["content"]
            }
        }
    }
]


# Load the OpenAI API key from a configuration file
with open("config.json", "r") as config_file:
    config = json.load(config_file)
    client = OpenAI(api_key=config.get("OPENAI_API_KEY"))

WORK_START = 8  # 8 AM
WORK_END = 18   # 6 PM
LUNCH_START = 12
LUNCH_END = 14
limit_answers = 5
limit_xml_sys_errors = 2
st.session_state.xml_errors = 0

weekdays = {0 : "Monday", 1 : "Tuesday", 2 : "Wednesday", 3 : "Thursday", 4 : "Friday", 5 : "Saturday", 6 : "Sunday"}

def get_users():
    query = "SELECT * FROM users"
    return pd.read_sql_query(query, conn)

    
def is_iso8601(date_string):
    try:
        datetime.fromisoformat(date_string)
        return True
    except ValueError:
        return False

def send_to_llm():
    """
    Communicates with OpenAI API to get a response for a given prompt.

    Args:
        new_prompt (str): The prompt to send to OpenAI API.

    Returns:
        str: The response from OpenAI API.
    """

    try:
        # Make a request to the OpenAI API
        response = client.chat.completions.with_raw_response.create(
            model="gpt-4o",  # Use "model" instead of "engine"
            messages=st.session_state.messages + [{"role": "system", "content": st.session_state.conformity_instructions}],
            tools=tools,
            max_tokens=2400,
            temperature=0
        )
        choice = response.parse().choices[0]
        print(choice)
        if(choice.finish_reason == "tool_calls"):
            arguments = choice.message.tool_calls[0].function.arguments
            name = choice.message.tool_calls[0].function.name
            st.session_state.messages.append({"role" : "assistant", "content" : None, "function_call" : {"arguments" : arguments, "name" : name}})
            data = choice.message.tool_calls[0].function
            api_answer = analyze_lambda_json(data)
            print(api_answer)
            st.session_state.messages.append({"role" : "function", "name" : choice.message.tool_calls[0].function.name,  "content" : api_answer})
            send_to_llm()
        else:
            message = choice.message.content.strip()
            message = {"role" : "assistant", "content" : message}
            st.session_state.messages.append(message)
            write_message(message)
    except Exception as e:
        print(f"Error: {str(e)}")
        st.session_state.messages.append({"role" : "assistant", "content" : "an error occurred. Please contact administrator if error persists"})

def get_email_by_name(name):
    try:
        # Execute the SQL query to find the email by name
        cursor.execute("SELECT email FROM users WHERE LOWER(name) = ?", (name,))
        # Fetch one result
        result = cursor.fetchone()
        return result
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None


def check_attendees(names):
    attendees = {key: None for key in names}
    for name in names:
        attendees[name] = get_email_by_name(name.lower())
    return json.dumps(attendees)


def get_users():
    query = "SELECT * FROM users"
    return pd.read_sql_query(query, conn)


def setup_meeting(data):
    title = data["title"]
    start_time = data["start_time"]
    end_time = data["end_time"]
    participants = data["attendees_by_email"]
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
        print(f"Error: {str(e)}")
        return json.dumps({"success" : "False",
                "description" : "Error while creating the meeting. Tell user to contact administrator if the error persist :  {e}"})
    return json.dumps({"success" : "True"})

def check_availabilities_json(data):
    return(json.dumps(check_availabilities(data)))

def check_availabilities(data):
    email_meetings = {}
    emails = data["attendees_by_email"]
    start_day = datetime.fromisoformat(data["start_day"])
    end_day = datetime.fromisoformat(data["end_day"])

    try:
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

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return f"Error while checking availabilities. Tell user to contact administrator if the error persists: {e}"

    # If proposed timeslot is provided, check availability
    if "proposed_timeslot_start_time" in data and "proposed_timeslot_end_time" in data:
        proposed_start_time = datetime.fromisoformat(data["proposed_timeslot_start_time"])
        proposed_end_time = datetime.fromisoformat(data["proposed_timeslot_end_time"])

        for email in emails:
            availability = True  # Assume the attendee is available by default

            # Fetch any meetings that overlap with the proposed timeslot
            try:
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

            except sqlite3.Error as e:
                print(f"An error occurred: {e}")
                return f"Error while checking availabilities. Tell user to contact administrator if the error persists: {e}"

            # Store availability result for the attendee
            email_meetings[email]["availability"] = availability

    return email_meetings


def propose_availabilities(data):
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
    def split_into_slots(intervals, meeting_duration):
        two_hour_slots = []
        for interval in intervals:
            slot_start = interval['start_time']
            while slot_start + timedelta(minutes=meeting_duration) <= interval['end_time']:
                slot_end = slot_start + timedelta(minutes=meeting_duration)
                if avoid_lunch_time({'start_time': slot_start, 'end_time': slot_end}):
                    two_hour_slots.append({'start_time': slot_start.strftime("%Y-%m-%dT%H:%M:%S"), 'end_time': slot_end.strftime("%Y-%m-%dT%H:%M:%S"), 'weekday': weekdays[slot_start.weekday()]})
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
        common_intervals = split_into_slots(common_intervals, meeting_duration)
        
        if common_intervals:
            common_intervals_per_day[day.date()] = common_intervals

    # Step 4: Prioritize proposing slots across different days
    proposed_slots = []
    for day, intervals in common_intervals_per_day.items():
        if intervals:  # If there's any available slot on this day
            proposed_slots.append(intervals[0])  # Just propose the first slot of each day

    return json.dumps({"common_timeslots" : proposed_slots})


def analyze_lambda_json(function_response):
    data = json.loads(function_response.arguments)
    func_name = function_response.name
    if func_name == "check_attendees":
        if("attendees_by_name" not in data):
            print("attendees_by_name not found")
            return "you didn't provide either attendees_by_name or attendees_by_email. Please provide it even with empty list."
        if not isinstance(data["attendees_by_name"], list):
            print("attendees_by_name is not a list.")
            return "attendees_by_name is not a list. Please provide it in a list format."
        return check_attendees(data["attendees_by_name"])
    if func_name == "setup_meeting":
        if "attendees_by_email" not in data:
            print("attendees is not provided")
            return "Please provide me attendees in list format"
        if "title" not in data:
            print("title is not provided")
            return "Please provide me the title of the meeting"
        if not isinstance(data["attendees_by_email"], list):
            print("attendees is not a list")
            return "Please provide me attendees in form of a list of emails"
        if "start_time" not in data:
            print("start_time not provided")
            return "Please provide me start_time in the ISO 8601 format : YYYY-MM-DDTHH:MM:SS"
        if "end_time" not in data:
            print("end_time not provided")
            return "Please provide me end_time in the ISO 8601 format : YYYY-MM-DDTHH:MM:SS"
        if not is_iso8601(data["start_time"]):
            print("start_time not provided is ISO Format")
            return "Please provide me start_time in the ISO 8601 format : YYYY-MM-DDTHH:MM:SS"
        if not is_iso8601(data["end_time"]):
            print("end_time not provided is ISO Format")
            return "Please provide me end_time in the ISO 8601 format : YYYY-MM-DDTHH:MM:SS"
        return setup_meeting(data)
    if func_name in ["check_availabilities", "propose_availabilities"]:
        if "attendees_by_email" not in data:
            print("attendees emails is not provided")
            return "Please provide me list of emails attendees_by_email"
        if "start_day" not in data:
            print("start_day is not provided")
            return "Please provide me start_day"
        if "end_day" not in data:
            print("end_day is not provided")
            return "Please provide me end_day"
        if func_name == "check_availabilities":
            return check_availabilities_json(data)
        else:
            return propose_availabilities(data)
    if func_name == "follow_up_action":
        if "content" not in data:
            print("content for follow-up action not provided")
            return "Please provide follow-up action content"
        write_message({"role" : "assistant", "content" : data["content"]})
    return {
                "error" : True,
                "description" : "unknown action provided. Please provide me one of the following actions {}.\n".format(allowed_actions)
            }

def write_message(message):
    if((message["role"] == "assistant") & (message["content"] is not None)):
        with st.chat_message("assistant"):
            st.markdown(message["content"])
    elif(message["role"] == "user"):
        with st.chat_message("user"):
            st.markdown(message["content"])

# Connect to the SQLite database
conn = sqlite3.connect('assistant.db')
cursor = conn.cursor()

today = date.today()
# Create a session with a specific region

allowed_actions = ["check_attendees", "setup_meeting", "check_availabilities", "propose_availabilities", "follow_up_action"]


if 'lambda_json_code' not in st.session_state:
        st.session_state.lambda_json_code =  {
        "message": "Json interactions will show up here"
    }

st.title("Json interactions :")

st.json(st.session_state.lambda_json_code)

st.title("List of Users :")

st.dataframe(get_users())

st.title("Meeting Assistant")

st.session_state.answers_count = 0

if "system_instructions" not in st.session_state:
    # Open the text file in read mode
    with open('initial_prompt.txt', 'r') as file:
        # Read the entire content of the file into a string variable
        st.session_state.system_instructions = file.read()

if "conformity_instructions" not in st.session_state:
    # Open the text file in read mode
    with open('conformity_prompt.txt', 'r') as file:
        # Read the entire content of the file into a string variable
        st.session_state.conformity_instructions = file.read()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": st.session_state.system_instructions},
                                {"role": "assistant", "content": "Hello ! How can I help you today ?"}]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    write_message(message)

# React to user input
if user_prompt := st.chat_input("What is up?"):
    if(user_prompt.strip()):
        # Display user message in chat message container
        st.session_state.answers_count = 0
        print("prompt received")
        with st.chat_message("user"):
            print(user_prompt)
            st.markdown(user_prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        send_to_llm()
        # Add assistant response to chat history
        st.rerun()