import streamlit as st
import json
from chatbot_backend.chatbot_bedrock.chat import invoke_with_text
from chatbot_backend.chatbot_bedrock.prompt_management import get_prompt
from chatbot_backend.chatbot_bedrock.prompts import DECIDE_ACTION, DEBUG_PROMPT
from chatbot_backend.configs import DECISION_PROMPT_ARN

st.title("Prompt 디버깅")

if "state" in st.session_state:

    chat_list = []

    for chat in st.session_state.state["messages"]:
        if chat["role"] == "user":
            row = {
                "user_prompt": chat["message"],
                "llm_decision": chat["action"],
                "decision_score": chat["score"]
            }
            if "filter" in chat:
                row["filter"] = chat["filter"]
            chat_list.append(row)

    if chat_list:

        selected_input = st.selectbox(
            "프롬프트 디버깅을 위해 사용할 고객 질문",
            [chat["user_prompt"] for chat in chat_list]
        )
        current_results = f'''{[chat["llm_decision"] for chat in chat_list if chat["user_prompt"]==selected_input].pop()}, {[chat["decision_score"] for chat in chat_list if chat["user_prompt"]==selected_input].pop()}'''

        col1, col2 = st.columns(2)
        with col1:
            st.text("선택된 다음 노드와 확률")
            st.text(current_results)


        with col2:
            expected_node = st.selectbox("기대 노드",
                                        ["update_filter", "recommend_personalized", "recommend_bestseller", "recommend_next", "search_image_from_user_input", "get_user_input"])

        current_prompt = st.text_area("Prompt",
                                      value=get_prompt(DECISION_PROMPT_ARN),
                                      height=650)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Bedrock 도움 받아보기"):
                payload = {
                    "prompt": current_prompt,
                    "results": current_results,
                    "expected results": f"{expected_node}, 0.95"
                }
                response = invoke_with_text(DEBUG_PROMPT, json.dumps(payload))
                st.text_area(
                    "Bedrock이 개선한 프롬프트",
                    value=response,
                    height=800)

        with col2:
            if st.button("프롬프트 테스트하기"):
                response = invoke_with_text(current_prompt, selected_input)
                st.text(response)

        if st.button("새로운 프롬프트 배포하기"):
            pass

    else:
        st.write("아직 입력한 채팅이 없습니다.")

else:
    st.write("사용자를 먼저 선택해주세요.")