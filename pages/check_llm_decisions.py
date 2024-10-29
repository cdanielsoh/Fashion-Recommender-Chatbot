import streamlit as st

st.title("Prompt 노드 결정과 필터 디버깅")

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
        st.dataframe(chat_list)

    else:
        st.write("아직 입력한 채팅 없습니다.")

else:
    st.write("사용자를 먼저 선택해주세요")