from chatbot_backend.chatbot_bedrock.prompts import DECIDE_ACTION, CATEGORICAL_METADATA, CREATE_FILTER_PROMPT, \
    FILTER_NEXT_ACTION_PROMPT, RECOMMEND_NEXT_ACTION_PROMPT, GET_USER_INPUT_PROMPT, RETRIEVE_SEARCH_KEYWORD_PROMPT, \
    NO_ITEMS_PROMPT
from chatbot_backend.chatbot_firehose.send_decision_log import send_record_to_firehose
from chatbot_backend.core import best_sellers_recommend, search_web_image, knn_search_with_image, \
    rerank_personalized_ranking, personalized_recommend_pg2
from chatbot_backend.configs import ITEMS_TO_SHOW
from chatbot_frontend.components.chat_history import remove_image_from_history, save_assistant_message
from chatbot_frontend.chat.stream_output import stream_assistant_output
from chatbot_frontend.chat.recommend import display_personalized_recommendations
from chatbot_backend.chatbot_bedrock.chat import invoke_with_text, invoke_stream_with_text
import streamlit as st
import json
from time import sleep


def get_user_input(state):
    chat_history = remove_image_from_history(state["messages"])
    assistant_message = stream_assistant_output(invoke_stream_with_text, GET_USER_INPUT_PROMPT, chat_history)
    current_action = 'get_user_input'
    return {"messages": save_assistant_message(assistant_message), "action": current_action}


def determine_action(state):
    user_input = remove_image_from_history(state["messages"])
    # res = json.loads(invoke_with_text(DECIDE_ACTION, user_input))
    next_action, score = invoke_with_text(DECIDE_ACTION, user_input).split(',')
    state["messages"][-1]["action"] = next_action
    state["messages"][-1]["score"] = score
    payload = {
        "user_prompt": state["messages"][-1]["message"],
        "llm_decision": next_action,
        "decision_score": score
    }
    send_record_to_firehose(payload)
    next_function = FUNCMAP[next_action]
    state_update = next_function(state)
    return state_update


def update_filter(state):
    with st.spinner("고객님의 취향 반영 중..."):
        latest_message = state["messages"][-1]["message"]
        user_input = f"""
            User input: {latest_message},
            Current filter: {state["current_filter"]},
            Categorical metadata: {CATEGORICAL_METADATA}
        """
        res = invoke_with_text(CREATE_FILTER_PROMPT, user_input)
        updated_filter = json.loads(res)
        current_action = 'update_filter'
    state["messages"][-1]["filter"] = updated_filter
    chat_history = remove_image_from_history(state["messages"])
    assistant_message = stream_assistant_output(invoke_stream_with_text, FILTER_NEXT_ACTION_PROMPT, chat_history)
    return {
        "current_filter": updated_filter,
        "action": current_action,
        "messages": save_assistant_message(assistant_message)
    }


def recommend_bestseller(state):
    with st.spinner("고객님의 취향을 기반으로 베스트셀러 추천을 시작합니다."):
        user_id, filters, current_recommendation = state["user_id"], state["current_filter"], state["current_recommendation"]
        recommendations = best_sellers_recommend(user_id, filters)
        display_personalized_recommendations(user_id, recommendations[current_recommendation:current_recommendation+ITEMS_TO_SHOW])
    chat_history = remove_image_from_history(state["messages"])
    if recommendations:
        assistant_message = stream_assistant_output(invoke_stream_with_text, RECOMMEND_NEXT_ACTION_PROMPT, chat_history)
    else:
        assistant_message = stream_assistant_output(invoke_stream_with_text, NO_ITEMS_PROMPT, chat_history)
    current_action = 'recommend_bestseller'
    return {
        "recommendations": recommendations,
        "current_recommendation": 0,
        "messages": save_assistant_message(assistant_message),
        "action": current_action
    }


def recommend_personalized(state):
    with st.spinner("고객님의 취향을 기반으로 고객님께 잘 어울리는 옷으로 구성된 개인화된 추천을 시작합니다."):
        user_id, filters, current_recommendation = state["user_id"], state["current_filter"], state["current_recommendation"]
        recommendations = personalized_recommend_pg2(user_id, filters)
        # recommendations = personalized_recommend(user_id, filters)
        display_personalized_recommendations(user_id, recommendations[current_recommendation:current_recommendation+ITEMS_TO_SHOW])
    chat_history = remove_image_from_history(state["messages"])
    if recommendations:
        assistant_message = stream_assistant_output(invoke_stream_with_text, RECOMMEND_NEXT_ACTION_PROMPT, chat_history)
    else:
        assistant_message = stream_assistant_output(invoke_stream_with_text, NO_ITEMS_PROMPT, chat_history)
    current_action = 'recommend_personalized'
    return {
        "recommendations": recommendations,
        "current_recommendation": 0,
        "messages": save_assistant_message(assistant_message),
        "action": current_action
    }


def recommend_next(state):
    with st.spinner("새로운 추천 아이템 생성중..."):
        user_id = state["user_id"]
        current_recommendation = state["current_recommendation"] + ITEMS_TO_SHOW
        recommendations = state["recommendations"]
        display_personalized_recommendations(user_id, recommendations[current_recommendation:current_recommendation + ITEMS_TO_SHOW])
    chat_history = remove_image_from_history(state["messages"])
    assistant_message = stream_assistant_output(invoke_stream_with_text, RECOMMEND_NEXT_ACTION_PROMPT, chat_history)
    current_action = 'recommend_next'
    return {
        "current_recommendation": current_recommendation,
        "messages": save_assistant_message(assistant_message),
        "action": current_action
    }


def search_image_from_user_input(state):
    user_id, current_recommendation = state["user_id"], state["current_recommendation"]
    with st.spinner("이미지 검색중..."):
        latest_message = state["messages"][-1]["message"]
        search_keyword = invoke_with_text(RETRIEVE_SEARCH_KEYWORD_PROMPT, latest_message)
    with st.spinner(f"{search_keyword} 검색중..."):
        sleep(1)
        found_image = search_web_image(search_keyword)
        st.image(found_image, width=400)
    with st.spinner("검색한 사진과 유사한 상품을 가져오는 중..."):
        sleep(1)
        item_list = knn_search_with_image(found_image)
    with st.spinner("고객 추천 순위로 재정렬중..."):
        sleep(1)
        recommendations = rerank_personalized_ranking(state["user_id"], item_list)
    display_personalized_recommendations(state["user_id"], recommendations[current_recommendation:current_recommendation+ITEMS_TO_SHOW])
    chat_history = remove_image_from_history(state["messages"])
    assistant_message = stream_assistant_output(invoke_stream_with_text, RECOMMEND_NEXT_ACTION_PROMPT,chat_history)
    current_action = 'recommend_personalized'
    return {
        "recommendations": recommendations,
        "current_recommendation": 0,
        "messages": save_assistant_message(assistant_message),
        "action": current_action
    }

FUNCMAP = {
    "get_user_input": get_user_input,
    "update_filter": update_filter,
    "recommend_personalized": recommend_personalized,
    "recommend_bestseller": recommend_bestseller,
    "recommend_next": recommend_next,
    "search_image_from_user_input": search_image_from_user_input
}
