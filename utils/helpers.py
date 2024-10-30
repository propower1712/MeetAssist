import streamlit as st
from utils.constants import *
import json
import logging
from openai import OpenAI
from utils.meetings_api_lambda import *
import random
import os


def get_lambda_answer(is_deployed, name, arguments, lambda_client = None, function_name = None):
    data = {"name" : name, "arguments" : json.loads(arguments)}
    logging.info("Lambda Called with following data - {}".format(data))
    if is_deployed:
        api_answer = invoke_lambda(lambda_client, function_name, data)
    else:
        api_answer = lambda_handler(data, None)
    return api_answer

@st.cache_data
def get_users(is_deployed, _lambda_client = None, _function_name = None):
    response = get_lambda_answer(is_deployed, "get_users_from_db", '{"content" : ""}', _lambda_client, _function_name)
    logging.info("Response is : {}".format(response))
    users_json = json.loads(json.loads(response)['api_response'])
    return pd.DataFrame(users_json)

def write_message(message):
    if((message["role"] == "assistant") & (message["content"] is not None)):
        with st.chat_message("assistant"):
            st.markdown(message["content"])
    elif(message["role"] == "user"):
        with st.chat_message("user"):
            st.markdown(message["content"])

@st.cache_data
def load_json(filename):
    # Load the external JSON file containing function definitions
    with open(filename, 'r') as file:
        logging.info("loading file - {}".format(filename))
        return(json.load(file))

def define_client(key):
    return OpenAI(api_key=key)


def invoke_lambda(lambda_client, function_name, payload=None):
    # Convert payload to JSON format if provided
    if payload is not None:
        payload = json.dumps(payload)

    try:
        # Call the Lambda function
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',  # 'Event' for async; 'RequestResponse' for sync
            Payload=payload  # Pass the JSON payload, or leave None if no payload needed
        )

        # Read the response payload
        response_payload = response['Payload'].read()
        response_data = json.loads(response_payload)
        return response_data
    except Exception as e:
        print("Error invoking Lambda:", e)
        return None