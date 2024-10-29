import streamlit as st
from chatbot_backend.core import rank_user_features, retrieve_past_user_chat_log
from chatbot_backend.chatbot_bedrock.chat import invoke_stream_with_text
from chatbot_backend.chatbot_bedrock.prompts import WELCOME_MESSAGE_PROMPT
import json
from time import sleep


def stream_string(text, delay=0.03):
    for word in text.split():
        yield word + " "
        sleep(delay)


def custom_json_stream_wrapper(bedrock_stream, stop):
    full_response = ""
    stop_yielding = False

    for chunk in bedrock_stream:
        full_response += chunk

        if stop in chunk and not stop_yielding:
            stop_yielding = True
            yield chunk[:chunk.index('{')]

        elif not stop_yielding:
            yield chunk

    filters = full_response.split('\n')

    filters_json = '\n'.join(filters[2:])
    if filters_json:
        filters = json.loads(filters_json)

        for category, values in filters.items():
            if category in st.session_state.filters:
                for value in values:
                    st.session_state.filters[category].append(value)
            else:
                st.session_state.filters[category] = values

    return full_response


def stream_assistant_output(bedrock_func, prompt, *_input, stream=True):
    with st.chat_message("assistant"):
        if stream:
            return st.write_stream(bedrock_func(prompt, *_input))

        else:
            return st.write_stream(custom_json_stream_wrapper(
                bedrock_func(prompt, *_input), "{"))


def stream_markdown_output(bedrock_func, prompt, *_input, stream=True):
    if stream:
        return st.write_stream(bedrock_func(prompt, *_input))

    else:
        return st.write_stream(custom_json_stream_wrapper(
            bedrock_func(prompt, *_input), "{"))


def welcome_user(user_id: str):
    try:
        user_preferences = st.session_state.user_preference
    except:
        user_preferences = rank_user_features(user_id)

    user_preferences['user_id'] = user_id[:5]
    user_preferences['past_chat_logs'] = retrieve_past_user_chat_log(user_id)

    full_response = stream_assistant_output(invoke_stream_with_text, WELCOME_MESSAGE_PROMPT, user_preferences)
    return full_response
