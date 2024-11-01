import streamlit as st
import re
import logging
from utils.helpers import *
from utils.meetings_api_lambda import *
import boto3

init_logging()

is_deployed = "FUNCTION_NAME" in os.environ
lambda_client = None
function_name = None
config = None
if is_deployed:
    lambda_client = boto3.client('lambda', region_name=os.getenv("REGION"))
    function_name = os.getenv("FUNCTION_NAME")
    openai_key = os.getenv("OPENAI_API_KEY")
else:
    config = load_json("config.json")
    openai_key = config.get("OPENAI_API_KEY")
    
client = define_client(os.getenv("OPENAI_API_KEY"))
tools = load_json("resources/tools_functions.json")


def send_to_llm():
    """
    Communicates with OpenAI API to get a response for a given prompt.
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
        if(choice.finish_reason == "tool_calls"):
            tool_call = choice.message.tool_calls[0]
            arguments = tool_call.function.arguments
            name = tool_call.function.name
            st.session_state.messages.append({"role" : "assistant", "content" : None, "function_call" : {"arguments" : arguments, "name" : name}})
            api_answer_json = get_lambda_answer(name, arguments, lambda_client, function_name)
            api_answer = json.loads(api_answer_json)
            logging.info("API Results - {}".format(api_answer))
            if(api_answer['func_name'] == "follow_up_action"):
                message = api_answer["api_response"]["message"]
                st.session_state.messages.append(message)
            st.session_state.messages.append({"role" : "function", "name" : name,  "content" : api_answer_json})
            send_to_llm()
        else:
            message = choice.message.content.strip()
            message = {"role" : "assistant", "content" : message}
            st.session_state.messages.append(message)
    except Exception as e:
        logging.error(f"Error: {str(e)}", exc_info=True)
        st.session_state.messages.append({"role" : "assistant", "content" : "an error occurred. Please contact administrator if error persists"})

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

if "app_presentation" not in st.session_state:
    # Open the text file in read mode
    with open('resources/app_presentation.txt', 'r') as file:
        # Read the entire content of the file into a string variable
        st.session_state.app_presentation = file.read()

st.title("Meeting Assistant")

# Display the explanation text in Streamlit
st.markdown(st.session_state.app_presentation)

st.title("List of Users :")

st.dataframe(get_users(lambda_client, function_name))

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
        with st.chat_message("user"):
            logging.info("User prompt - {}".format(user_prompt))
            st.markdown(user_prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        send_to_llm()
        # Add assistant response to chat history
        st.rerun()