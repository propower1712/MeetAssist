import streamlit as st
from openai import OpenAI
import pandas as pd
import re
import logging
from utils.helpers import *

init_logging()

tools = load_json("resources/tools_functions.json")
config = load_json("config.json")
client = define_client(config.get("OPENAI_API_KEY"))


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
        logging.info("Choice result - {}".format(choice))
        if(choice.finish_reason == "tool_calls"):
            arguments = choice.message.tool_calls[0].function.arguments
            name = choice.message.tool_calls[0].function.name
            st.session_state.messages.append({"role" : "assistant", "content" : None, "function_call" : {"arguments" : arguments, "name" : name}})
            data = choice.message.tool_calls[0].function
            api_answer = analyze_lambda_json(data)
            logging.info("API Results - {}".format(api_answer))
            st.session_state.messages.append({"role" : "function", "name" : choice.message.tool_calls[0].function.name,  "content" : api_answer})
            send_to_llm()
        else:
            message = choice.message.content.strip()
            message = {"role" : "assistant", "content" : message}
            st.session_state.messages.append(message)
            write_message(message)
    except Exception as e:
        logging.error(f"Error: {str(e)}", exc_info=True)
        st.session_state.messages.append({"role" : "assistant", "content" : "an error occurred. Please contact administrator if error persists"})


st.title("List of Users :")

st.dataframe(get_users())

st.title("Meeting Assistant")

st.session_state.answers_count = 0

if "system_instructions" not in st.session_state:
    # Open the text file in read mode
    with open('resources/initial_prompt.txt', 'r') as file:
        # Read the entire content of the file into a string variable
        st.session_state.system_instructions = file.read()

if "conformity_instructions" not in st.session_state:
    # Open the text file in read mode
    with open('resources/conformity_prompt.txt', 'r') as file:
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
        with st.chat_message("user"):
            logging.info("User prompt - {}".format(user_prompt))
            st.markdown(user_prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        send_to_llm()
        # Add assistant response to chat history
        st.rerun()