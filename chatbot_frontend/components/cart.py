import streamlit as st
from chatbot_backend.core import get_product_desc
from chatbot_backend.chatbot_msk.orders import submit_order


@st.dialog("비교함 등록 완료")
def add_to_compare(img):
    st.write(f"비교함에 {img['features']['product_name']}를 담았습니다.")
    st.session_state.compare_items.append(img)


@st.dialog("장바구니에 담기 완료")
def add_to_cart(img):
    st.write(f"장바구니에 {img['features']['product_name']}를 담았습니다.")
    st.session_state.cart.append(img)


@st.dialog("비교함")
def compare_items_dialog(images):
    if st.session_state.compare_items:
        containers = st.tabs([img["features"]["product_name"] for img in st.session_state.compare_items])

        for num, img in enumerate(images):
            with containers[num]:
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img["image"], width=200, use_column_width=False)

                    if st.button("장바구니 추가하기", key=img["item_id"]):
                        st.write(f"장바구니에 {img['features']['product_name']}를 담았습니다.")
                        st.session_state.cart.append(img)

                with col2:
                    st.subheader("스타일")
                    st.write(img["features"]["style"])
                    st.subheader("소재")
                    st.write(img["features"]["material"])
                    st.subheader("상품 설명")
                    st.write(get_product_desc(img["item_id"]))
                    st.subheader("가격")
                    st.write(f'{int(img["features"]["price"]):,}원')

    else:
        st.subheader("비교함에 담긴 상품이 없습니다.")


@st.dialog("장바구니")
def cart_items_dialog(images):
    if st.session_state.cart:
        containers = st.tabs([img["features"]["product_name"] for img in st.session_state.cart])

        for num, img in enumerate(images):
            with containers[num]:
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img["image"], width=200, use_column_width=False)


                with col2:
                    st.subheader("스타일")
                    st.write(img["features"]["style"])
                    st.subheader("소재")
                    st.write(img["features"]["material"])
                    st.subheader("상품 설명")
                    st.write(get_product_desc(img["item_id"]))
                    st.subheader("가격")
                    st.write(f'{int(img["features"]["price"]):,}원')

        if st.button("구매하기"):
            st.write("상품 구매 완료")
            submit_order(st.session_state.state["user_id"],
                         st.session_state.cart,
                         'Purchase')

    else:
        st.subheader("장바구니에 담긴 상품이 없습니다.")


def display_compare_items(images):
    if st.sidebar.button("비교함 확인하기"):
        compare_items_dialog(images)


def display_cart_items(images):
    # images = [d["image"] for d in state["messages"] if "image" in d]
    if st.sidebar.button("장바구니"):
        cart_items_dialog(images)
