import streamlit as st
from chatbot_frontend.components.chat_history import save_assistant_message, remove_image_from_history
from chatbot_frontend.chat.stream_output import stream_assistant_output, stream_markdown_output, stream_string
from chatbot_backend.chatbot_bedrock.chat import generate_recommendation, invoke_stream_with_text, \
    invoke_interaction_flow
from chatbot_backend.chatbot_bedrock.prompts import GENERATE_RECOMMEND_PERSONALIZED_RANKING, \
    RECOMMEND_NEXT_ACTION_PROMPT
from chatbot_backend.core import knn_search_with_image, rerank_personalized_ranking, get_item_images, \
    rank_user_features, best_sellers_recommend, personalized_recommend_pg
from chatbot_backend.chatbot_aurora.pgvector import get_item_list_features, get_connection
from chatbot_backend.configs import AURORA_CUSTOMER_DB_NAME, ITEMS_TO_SHOW
import base64
from io import BytesIO
from time import sleep
from chatbot_frontend.components.cart import add_to_cart, add_to_compare
import json
from random import random


def display_personalized_recommendations(user_id, recommend_list):

    images_dict = get_item_images(recommend_list)

    for item in recommend_list:
        st.session_state.recommended_items.append(item)

    features = get_item_list_features(get_connection(AURORA_CUSTOMER_DB_NAME), recommend_list)

    try:
        user_preference = st.session_state.user_preference

    except:
        user_preference = rank_user_features(user_id)

    show_items_in_column(images_dict, features, user_preference)


def display_personalized_rank(user_id, image, recommend_number):
    st.session_state.uploaded_image = image
    with st.spinner(text="유사한 상품 검색중..."):
        knn_list = knn_search_with_image(image)

    with st.spinner(text=f"{user_id[:5]}님의 선호도 분석중..."):
        recommend_list = rerank_personalized_ranking(user_id, knn_list)
        sleep(3)

    st.session_state.state["recommendations"] = recommend_list

    limited_recommend_list = recommend_list[:recommend_number]

    images_dict = get_item_images(limited_recommend_list)

    features = get_item_list_features(get_connection(AURORA_CUSTOMER_DB_NAME), limited_recommend_list)

    try:
        user_preference = st.session_state.user_preference

    except:
        user_preference = rank_user_features(user_id)

    show_items_in_column(images_dict, features, user_preference)


def display_interaction_flow(user_context, current_filter):
    user_context = [{k: v for k, v in d.items() if k != 'image'} for d in user_context]
    for response in invoke_interaction_flow(user_context, current_filter):
        if 'flowOutputEvent' in response:
            node_name = response['flowOutputEvent']['nodeName']
            content = response['flowOutputEvent']['content']['document']

            if 'filterContext' in node_name:
                with st.chat_message("assistant"):
                    st.write_stream(stream_string(content))
                    st.session_state.state["messages"].append(save_assistant_message(content))

            if 'Json' in node_name:
                content = json.loads(content)
                st.session_state.state["current_filter"] = content

            if 'campaignName' in node_name:
                state = st.session_state.state
                if content == 'best-sellers':
                    with st.spinner("고객님의 취향을 기반으로 베스트셀러 추천을 시작합니다."):
                        user_id, filters, current_recommendation = state["user_id"], state["current_filter"], state[
                            "current_recommendation"]
                        recommendations = best_sellers_recommend(user_id, filters)
                        display_personalized_recommendations(user_id, recommendations[
                                                                      current_recommendation:current_recommendation + ITEMS_TO_SHOW])
                    chat_history = remove_image_from_history(state["messages"])
                    assistant_message = stream_assistant_output(invoke_stream_with_text, RECOMMEND_NEXT_ACTION_PROMPT,
                                                                chat_history)
                    st.session_state.state["messages"].append(save_assistant_message(assistant_message))
                else:
                    with st.spinner("고객님의 취향을 기반으로 고객님께 잘 어울리는 옷으로 구성된 개인화된 추천을 시작합니다."):
                        user_id, filters, current_recommendation = state["user_id"], state["current_filter"], state["current_recommendation"]
                        recommendations = personalized_recommend_pg(user_id, filters)
                        display_personalized_recommendations(user_id, recommendations[
                                                                      current_recommendation:current_recommendation + ITEMS_TO_SHOW])
                    chat_history = remove_image_from_history(state["messages"])
                    assistant_message = stream_assistant_output(invoke_stream_with_text, RECOMMEND_NEXT_ACTION_PROMPT,
                                                                chat_history)
                    st.session_state.state["messages"].append(save_assistant_message(assistant_message))


def show_items_in_column(images_dict, features, user_preference):
    row = st.columns(ITEMS_TO_SHOW)
    for col_no, (img_key, img_value) in enumerate(images_dict.items()):
        column = row[col_no]
        decoded_image = BytesIO(base64.b64decode(img_value))
        with column:
            with st.container(height=500):
                product_name = features[int(img_key)]['product_name']
                st.markdown(product_name)

                st.image(decoded_image, caption=f'{int(features[int(img_key)]["price"]):,}원')

                response = stream_markdown_output(generate_recommendation, GENERATE_RECOMMEND_PERSONALIZED_RANKING,
                                                   user_preference, img_value, features[int(img_key)])

                img = {
                    "image": decoded_image,
                    "item_id": img_key,
                    "features": features[int(img_key)],
                    "reason": response
                }

                if st.button("비교 목록에 담기", key=f'{img_key}-compare-{random()}'):
                    add_to_compare(img)

                if st.button("장바구니에 담기", key=f'{img_key}-cart-{random()}'):
                    add_to_cart(img)

        message = save_assistant_message(response)
        message['image'] = img

        st.session_state.state["messages"].append(message)