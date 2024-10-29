import streamlit as st
from chatbot_backend.configs import ITEMS_TO_SHOW
from chatbot_backend.core import save_chat_logs
from chatbot_frontend.graph.graph_state import SessionState, update_state
from chatbot_frontend.components.images import upload_image, assess_image
from chatbot_frontend.chat.recommend import display_personalized_rank
from chatbot_frontend.chat.stream_output import welcome_user
from chatbot_frontend.components.chat_history import chat_history_dropdown, save_user_message, \
    save_assistant_message, remove_image_from_history
from chatbot_frontend.graph.graph_nodes import determine_action
from chatbot_frontend.components.chat_history import display_session_history
from chatbot_frontend.components.cart import display_cart_items, display_compare_items
import time


def main():

    st.title("Personal Shopping Assistant Demo")

    user_ids = ['55d15396193dfd45836af3a6269a079efea339e875eff42cc0c228b002548a9d',
                '55eff9509234639ac898afd57fc8ab9b94afc0fc0cdac6b8ac6710eb23495dcb',
                'b257688d1f6fce7521ce2300529a6c7ae07afa0caef1be0c94d73a6a9f694b8c',
                'be1981ab818cf4ef6765b2ecaea7a2cbf14ccd6e8a7ee985513d9e8e53c6d91b',
                '148576523dcc76cee4e209e91cd3ac70269ea27faa3a3b8468f82664562a4f7e',
                '41c0ba84ef309296d5d2055defe96fadcf97b6dee9255ab002cbb2fbaa900f00']

    user_id_expander = st.sidebar.expander("Select User")

    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    with user_id_expander:
        if st.session_state.user_id is None:
            st.session_state.user_id = st.selectbox("사용자 선택", user_ids, index=None, placeholder="사용자를 선택하세요")

        else:
            st.text(f"{st.session_state.user_id}")

    if st.session_state.user_id is not None:

        if "state" not in st.session_state:
            st.session_state.state = SessionState(
                    user_id=st.session_state.user_id,
                    messages=[],
                    current_filter={},
                    action="get_user_input",
                    recommendations=[],
                    current_recommendation=0
            )

            st.session_state.welcome = False
            st.session_state.uploaded_image = None
            st.session_state.recommended_items = []
            st.session_state.compare_items = []
            st.session_state.cart = []
            st.session_state.timestamp = int(time.time())

        past_chat_expander = st.sidebar.expander("Chat History")

        upload_image_expander = st.sidebar.expander("Upload Image")

        display_compare_items(st.session_state.compare_items)

        display_cart_items(st.session_state.cart)

        chat_history_dropdown(past_chat_expander, st.session_state.user_id)

        uploaded_image = upload_image(upload_image_expander)

        if st.session_state.welcome:
            display_session_history(st.session_state.state["messages"])
        else:
            welcome_message = welcome_user(st.session_state.state["user_id"])
            st.session_state.state["messages"].append(save_assistant_message(welcome_message))
            st.session_state.welcome = True

        if uploaded_image != st.session_state.uploaded_image and assess_image(uploaded_image):
            display_personalized_rank(st.session_state.user_id, uploaded_image, ITEMS_TO_SHOW)

        if user_input := st.chat_input():

            st.session_state.state["messages"].append(save_user_message(user_input))

            with st.chat_message("user"):
                st.markdown(user_input)

            state_update = determine_action(st.session_state.state)

            st.session_state.state = update_state(st.session_state.state, state_update)

        if st.session_state.recommended_items:
            save_chat_logs(st.session_state.user_id, st.session_state.timestamp,
                           remove_image_from_history(st.session_state.state["messages"]), st.session_state.recommended_items)


if __name__ == "__main__":
    main()