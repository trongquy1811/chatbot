import os

import httpx
import streamlit as st


st.set_page_config(
    page_title="DocAnalyzer AI",
    page_icon="📄",
    layout="wide",
)

st.title("📄 DocAnalyzer AI")
st.caption(
    "Phân tích tài liệu · Hỏi đáp có nguồn · Bộ nhớ hội thoại"
)

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000",
).rstrip("/")


with st.sidebar:
    st.header("Kết nối")

    token = st.text_input(
        "Access token",
        type="password",
    )

    if st.session_state.get("identity_token") != token:
        for key in [
            "conversation_id",
            "document_picker",
        ]:
            st.session_state.pop(key, None)

        st.session_state.identity_token = token


if not token:
    st.info("Nhập access token ở thanh bên để bắt đầu.")
    st.stop()


def api(method, route, **kwargs):
    try:
        response = httpx.request(
            method,
            API_BASE_URL + route,
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=600,
            **kwargs,
        )

        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get(
                "detail",
                "Yêu cầu thất bại",
            )
        except ValueError:
            detail = "Yêu cầu thất bại"

        st.error(
            f"{exc.response.status_code}: {detail}"
        )
        st.stop()

    except httpx.RequestError:
        st.error(
            "Không kết nối được backend. "
            "Kiểm tra API_BASE_URL và trạng thái API."
        )
        st.stop()


def show_sources(sources):
    for source in sources:
        st.markdown(
            f"**{source['name']} "
            f"· trang {source['page']}**"
        )
        st.code("source:" + source["id"])
        st.write(source["excerpt"])


with st.sidebar:
    st.divider()
    st.header("Tài liệu")

    uploaded = st.file_uploader(
        "Tải tài liệu hoặc hình ảnh",
        type=[
            "pdf",
            "txt",
            "md",
            "markdown",
            "png",
            "jpg",
            "jpeg",
        ],
    )

    if st.button(
        "Xử lý tài liệu",
        disabled=uploaded is None,
    ):
        with st.spinner("Đang đọc và lập chỉ mục…"):
            api(
                "POST",
                "/documents",
                files={
                    "file": (
                        uploaded.name,
                        uploaded.getvalue(),
                        uploaded.type,
                    )
                },
            )

        st.success("Đã xử lý tài liệu")
        st.rerun()

    documents = api("GET", "/documents")

    ready_documents = {
        item["id"]: item
        for item in documents
        if item["status"] == "ready"
    }

    selected_documents = st.multiselect(
        "Tài liệu dùng để trả lời",
        options=list(ready_documents),
        format_func=lambda item_id: (
            ready_documents[item_id]["name"]
        ),
        key="document_picker",
    )

    with st.expander("Quản lý tài liệu"):
        for document in documents:
            st.write(
                f"{document['name']} "
                f"— {document['status']}"
            )

            if st.button(
                "Xóa",
                key="delete_" + document["id"],
            ):
                api(
                    "DELETE",
                    "/documents/" + document["id"],
                )

                st.session_state.pop(
                    "document_picker",
                    None,
                )
                st.rerun()

    st.divider()
    st.header("Hội thoại")

    if st.button("Hội thoại mới"):
        conversation = api(
            "POST",
            "/conversations",
            json={"title": "Hội thoại mới"},
        )

        st.session_state.conversation_id = (
            conversation["id"]
        )
        st.rerun()

    conversations = api(
        "GET",
        "/conversations",
    )

    if not conversations:
        conversation = api(
            "POST",
            "/conversations",
            json={"title": "Hội thoại đầu tiên"},
        )

        st.session_state.conversation_id = (
            conversation["id"]
        )
        st.rerun()

    conversation_lookup = {
        item["id"]: item["title"]
        for item in conversations
    }

    conversation_ids = list(conversation_lookup)
    current_id = st.session_state.get(
        "conversation_id"
    )

    selected_index = (
        conversation_ids.index(current_id)
        if current_id in conversation_ids
        else 0
    )

    conversation_id = st.selectbox(
        "Chọn hội thoại",
        options=conversation_ids,
        index=selected_index,
        format_func=lambda item_id: (
            conversation_lookup[item_id]
            + " · "
            + item_id[:8]
        ),
    )

    st.session_state.conversation_id = conversation_id

    remember = st.checkbox(
        "Ghi nhớ thông tin tôi yêu cầu lưu",
        value=False,
        help=(
            "Chỉ trích xuất từ câu hỏi của bạn. "
            "Thông tin mâu thuẫn cần xác nhận "
            "trong tab Bộ nhớ."
        ),
    )


chat_tab, memory_tab = st.tabs([
    "Hỏi đáp",
    "Bộ nhớ",
])


with chat_tab:
    history = api(
        "GET",
        f"/conversations/{conversation_id}/messages",
    )

    for message in history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message.get("sources"):
                with st.expander("Nguồn đã dùng"):
                    show_sources(message["sources"])

    question = st.chat_input(
        "Hỏi về tài liệu đã chọn…"
    )

    if question:
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("Đang phân tích…"):
                result = api(
                    "POST",
                    "/chat",
                    json={
                        "question": question,
                        "conversation_id": conversation_id,
                        "document_ids": selected_documents,
                        "remember": remember,
                    },
                )

            st.markdown(result["answer"])

            with st.expander("Nguồn tham khảo"):
                show_sources(result["sources"])

            if result["memory"].get("conflicts"):
                st.warning(
                    "Có thông tin bộ nhớ mâu thuẫn. "
                    "Mở tab Bộ nhớ để xác nhận."
                )

            if result["memory"]["status"] == "failed":
                st.warning(
                    "Câu trả lời đã lưu nhưng chưa "
                    "cập nhật được bộ nhớ."
                )

            with st.expander("Chi tiết xử lý"):
                st.caption(
                    "Trace ID: " + result["trace_id"]
                )
                st.json(result["trace"])


with memory_tab:
    st.caption(
        "Bộ nhớ cá nhân được dùng giữa các hội thoại. "
        "Xóa bộ nhớ không xóa tin nhắn gốc."
    )

    memories = api("GET", "/memories")

    if not memories:
        st.info("Chưa có thông tin được ghi nhớ.")

    for memory in memories:
        st.markdown(
            f"**{memory['key']}**: {memory['value']}"
        )

        if memory["pending_value"] is not None:
            st.warning(
                "Thông tin mới: "
                + memory["pending_value"]
            )

            left, right = st.columns(2)

            if left.button(
                "Dùng thông tin mới",
                key="accept_" + memory["id"],
            ):
                api(
                    "POST",
                    f"/memories/{memory['id']}/resolve",
                    json={"accept": True},
                )
                st.rerun()

            if right.button(
                "Giữ thông tin cũ",
                key="reject_" + memory["id"],
            ):
                api(
                    "POST",
                    f"/memories/{memory['id']}/resolve",
                    json={"accept": False},
                )
                st.rerun()

        if st.button(
            "Quên thông tin này",
            key="forget_" + memory["id"],
        ):
            api(
                "DELETE",
                f"/memories/{memory['id']}",
            )
            st.rerun()