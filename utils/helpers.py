import streamlit as st
from utils.constants import *
import json
import logging
from openai import OpenAI
import random


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