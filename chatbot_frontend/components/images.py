import streamlit as st
from PIL import Image
from chatbot_frontend.components.chat_history import save_assistant_message
from chatbot_frontend.chat.stream_output import stream_assistant_output
from chatbot_backend.chatbot_bedrock.chat import describe_image
from chatbot_backend.chatbot_bedrock.prompts import ASSESS_IMAGE_PROMPT
from chatbot_backend.core import encode_image
from time import sleep

def upload_image(container):
    with container:
        uploaded_image = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

        if uploaded_image is not None and uploaded_image != st.session_state.uploaded_image:
            image = Image.open(uploaded_image)

            return image


def assess_image(image):
    st.image(image, width=200)

    encoded_image = encode_image(image)

    with st.spinner(text="업로드하신 사진 분석중..."):
        sleep(1)
        response = stream_assistant_output(describe_image, ASSESS_IMAGE_PROMPT, encoded_image)

        message = save_assistant_message(response)

        st.session_state.state["messages"].append(message)

    return False if "죄송합니다" in response else True
