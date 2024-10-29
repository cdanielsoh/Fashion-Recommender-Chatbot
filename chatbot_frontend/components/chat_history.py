import streamlit as st
from chatbot_backend.chatbot_aurora.pgvector import get_item_list_features, get_connection
from chatbot_backend.core import retrieve_past_recommendations, get_item_images
from io import BytesIO
import base64
from chatbot_frontend.components.cart import add_to_cart, add_to_compare
from chatbot_backend.configs import AURORA_CUSTOMER_DB_NAME


def save_assistant_message(message):
    return {"role": "assistant", "message": message}


def save_user_message(message):
    return {"role": "user", "message": message}


def remove_image_from_history(messages):
    return [{k: v for k, v in message.items() if k != "image"}  for message in messages]


def chat_history_dropdown(container: st.container, user_id):
    chat_history = retrieve_past_recommendations(user_id)
    with container:
        if chat_history:
            for tstamp, content in chat_history.items():
                if st.button(label=str(tstamp), key=tstamp):
                    chat_history_dialog(tstamp, content)
        else:
            st.write("채팅 기록이 없습니다.")


@st.dialog("Chat history")
def chat_history_dialog(tstamp, content):
    st.subheader(f"{tstamp}에 받아보신 추천 상품입니다.")
    item_images = get_item_images(content)
    features = get_item_list_features(get_connection(AURORA_CUSTOMER_DB_NAME), content)

    for item_key in content:
        with st.container(border=True):
            col1, col2 = st.columns(2)

            with col1:
                st.image(BytesIO(base64.b64decode(item_images[item_key])),
                         width=200, use_column_width=False)

            with col2:
                st.subheader("스타일")
                st.write(features[int(item_key)]["style"])
                st.subheader("소재")
                st.write(features[int(item_key)]["material"])
                st.subheader("상품 설명")
                st.write(features[int(item_key)]["product_desc"])
                st.subheader("가격")
                st.write(f'{int(features[int(item_key)]["price"]):,}원')


def display_image_with_recommendation(images):
    col_no = len(images)
    cols = st.columns(col_no)
    for col, img in zip(cols, images):
        with col:
            with st.container(height=500):
                product_name = img['features']['product_name']
                st.markdown(product_name)

                st.image(img["image"], caption=f'{int(img["features"]["price"]):,}원')

                st.markdown(img["reason"])

                try:

                    if st.button("비교 목록에 담기", key=f'{img["item_id"]}-compare'):  # , on_click=add_to_compare, args=(img,)):
                        add_to_compare(img)

                    if st.button("장바구니에 담기", key=f'{img["item_id"]}-cart'):  # , on_click=add_to_cart, args=(img,)):
                        add_to_cart(img)

                except:
                    pass


def display_session_history(messages):
    img_count = 0
    images = []
    for message in messages:
        if "image" in message.keys():
            img_count += 1
            images.append(message["image"])
        else:
            with st.chat_message(message["role"]):
                st.markdown(message["message"])

        if img_count % 3 == 0 and img_count > 0:
            display_image_with_recommendation(images)
            images = []
            img_count = 0
