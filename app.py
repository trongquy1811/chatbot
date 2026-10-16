import os
import sys
import httpx
import streamlit as st

# Auto-launch with streamlit if user accidentally ran `python app.py` directly in console
if __name__ == "__main__" and "streamlit.runtime" not in sys.modules and not os.environ.get("STREAMLIT_SERVER_PORT"):
    import subprocess
    cmd = [sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))

st.set_page_config(
    page_title="Agent Harness Chatbot",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Agent Harness Chatbot")
st.caption(
    "Kiến trúc Agent Harness · Gemini LLM · Qdrant Vector Search · Redis Cache · PostgreSQL Memory"
)

# API URL: support environment variable, default to http://127.0.0.1:8000
DEFAULT_API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def api_request(base_url: str, method: str, route: str, token: str | None = None, **kwargs):
    """Perform HTTP request to backend with error handling."""
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = httpx.request(
            method,
            f"{base_url}{route}",
            headers=headers,
            timeout=120.0,
            **kwargs,
        )
        return response
    except httpx.RequestError as exc:
        st.error(
            f"❌ Không thể kết nối đến Backend tại `{base_url}`: {exc}. "
            "Vui lòng đảm bảo rằng Backend API đang chạy (ví dụ: `uvicorn backend.main:app --port 8000`)."
        )
        st.stop()
        return None


def show_sources(sources: list[dict]):
    if not sources:
        st.info("Không có tài liệu tham khảo nào được trích dẫn.")
        return

    for source in sources:
        st.markdown(
            f"**📄 {source.get('name', 'Tài liệu')}** (Trang {source.get('page', 1)})"
        )
        st.caption(f"Source ID: `{source.get('id', '')}`")
        st.write(source.get("excerpt", ""))
        st.divider()


def main():
    # ==========================================
    # SIDEBAR: CONNECTION & AUTHENTICATION
    # ==========================================
    with st.sidebar:
        st.header("⚙️ Kết nối & Xác thực")

        api_url = st.text_input(
            "Backend API URL",
            value=DEFAULT_API_URL,
            help="Địa chỉ FastAPI Backend server",
        ).rstrip("/")

        # Default demo token from config for easy local testing
        default_token = "sec_tok_0123456789abcdef0123456789"
        token_input = st.text_input(
            "Nhập Access Token",
            value=st.session_state.get("auth_token", default_token),
            type="password",
            help="Token tối thiểu 24 ký tự. Token mẫu: sec_tok_0123456789abcdef0123456789",
        ).strip()

        if st.session_state.get("auth_token") != token_input:
            st.session_state.auth_token = token_input
            st.session_state.auth_user = None
            for key in ["conversation_id", "document_picker"]:
                st.session_state.pop(key, None)

        # 1. Đăng nhập: kiểm tra Access token thành công trước khi hiển thị chức năng
        if not token_input:
            st.warning("Vui lòng nhập Access Token để truy cập hệ thống.")
            st.stop()
            return

        # Verify token against backend
        verify_res = api_request(api_url, "GET", "/auth/verify", token=token_input)
        if verify_res is None:
            st.stop()
            return

        if verify_res.status_code == 401:
            st.error("❌ Access Token không hợp lệ hoặc chưa được đăng ký trong API_KEYS_JSON.")
            st.info("💡 Token demo mặc định: `sec_tok_0123456789abcdef0123456789`")
            st.stop()
            return
        elif verify_res.status_code != 200:
            st.error(f"Lỗi kiểm tra xác thực (HTTP {verify_res.status_code}): {verify_res.text}")
            st.stop()
            return

        auth_data = verify_res.json()
        st.session_state.auth_user = auth_data.get("owner", "Unknown")
        st.success(f"Đã đăng nhập: **{st.session_state.auth_user}**")

    token = st.session_state.auth_token

    # ==========================================
    # SIDEBAR: DOCUMENTS & CONVERSATIONS
    # ==========================================
    with st.sidebar:
        st.divider()
        st.header("📁 Quản lý Tài liệu")

        uploaded = st.file_uploader(
            "Tải tài liệu tham khảo",
            type=["pdf", "txt", "md", "markdown", "png", "jpg", "jpeg"],
            help="Hỗ trợ PDF, Text, Markdown và hình ảnh (OCR tự động).",
        )

        analyze_images = st.checkbox(
            "Phân tích toàn bộ hình ảnh trong PDF (OCR)",
            value=False,
            help="Bật tùy chọn này nếu PDF chứa nhiều biểu đồ hoặc scan hình ảnh.",
        )

        if st.button("📤 Tải lên & Xử lý", disabled=uploaded is None):
            with st.spinner("Đang trích xuất nội dung, chia chunk và lập chỉ mục Qdrant..."):
                res = api_request(
                    api_url,
                    "POST",
                    "/documents",
                    token=token,
                    params={"analyze_all_images": analyze_images},
                    files={
                        "file": (
                            uploaded.name,
                            uploaded.getvalue(),
                            uploaded.type or "application/octet-stream",
                        )
                    },
                )
                if res and res.status_code == 200:
                    st.success("Tài liệu đã được tải lên và sẵn sàng!")
                    st.rerun()
                elif res:
                    detail = res.json().get("detail", res.text)
                    st.error(f"Tải lên thất bại ({res.status_code}): {detail}")

        # Fetch documents list
        doc_res = api_request(api_url, "GET", "/documents", token=token)
        documents = doc_res.json() if (doc_res and doc_res.status_code == 200) else []

        ready_docs = {d["id"]: d for d in documents if d["status"] == "ready"}

        selected_documents = st.multiselect(
            "Chọn tài liệu cho câu hỏi:",
            options=list(ready_docs.keys()),
            format_func=lambda did: ready_docs[did]["name"],
            key="document_picker",
        )

        with st.expander(f"Danh sách tài liệu ({len(documents)})"):
            for doc in documents:
                status_badge = "✅" if doc["status"] == "ready" else "⏳" if doc["status"] == "processing" else "❌"
                st.markdown(f"{status_badge} **{doc['name']}** ({doc['chunks']} chunks)")
                if st.button("🗑️ Xóa", key=f"del_doc_{doc['id']}"):
                    del_res = api_request(api_url, "DELETE", f"/documents/{doc['id']}", token=token)
                    if del_res and del_res.status_code == 200:
                        st.session_state.pop("document_picker", None)
                        st.rerun()
                    else:
                        st.error("Không thể xóa tài liệu.")

        st.divider()
        st.header("💬 Hội thoại")

        if st.button("➕ Hội thoại mới"):
            new_conv = api_request(
                api_url,
                "POST",
                "/conversations",
                token=token,
                json={"title": "Hội thoại mới"},
            )
            if new_conv and new_conv.status_code == 200:
                st.session_state.conversation_id = new_conv.json()["id"]
                st.rerun()

        conv_res = api_request(api_url, "GET", "/conversations", token=token)
        conversations = conv_res.json() if (conv_res and conv_res.status_code == 200) else []

        if not conversations:
            initial_conv = api_request(
                api_url,
                "POST",
                "/conversations",
                token=token,
                json={"title": "Hội thoại mặc định"},
            )
            if initial_conv and initial_conv.status_code == 200:
                st.session_state.conversation_id = initial_conv.json()["id"]
                st.rerun()
            conversations = []

        conv_lookup = {c["id"]: c["title"] for c in conversations}
        conv_ids = list(conv_lookup.keys())

        curr_cid = st.session_state.get("conversation_id")
        sel_idx = conv_ids.index(curr_cid) if curr_cid in conv_ids else 0

        conversation_id = st.selectbox(
            "Chọn cuộc hội thoại:",
            options=conv_ids,
            index=sel_idx if conv_ids else 0,
            format_func=lambda cid: f"{conv_lookup[cid]} ({cid[:6]})",
        )
        st.session_state.conversation_id = conversation_id

        st.divider()
        remember_toggle = st.checkbox(
            "🧠 Cho phép ghi nhớ thông tin (Memory)",
            value=False,
            help="Khi bật, AI sẽ trích xuất facts từ câu hỏi để lưu vào bộ nhớ dài hạn.",
        )

    # ==========================================
    # MAIN INTERFACE TABS
    # ==========================================
    chat_tab, memory_tab = st.tabs(["💬 Hỏi đáp RAG", "🧠 Quản lý Bộ nhớ"])

    with chat_tab:
        # Load conversation history
        if conversation_id:
            msg_res = api_request(
                api_url,
                "GET",
                f"/conversations/{conversation_id}/messages",
                token=token,
            )
            history = msg_res.json() if (msg_res and msg_res.status_code == 200) else []

            for msg in history:
                role = msg["role"]
                content = msg["content"]
                sources = msg.get("sources", [])

                with st.chat_message(role):
                    st.markdown(content)
                    if sources:
                        with st.expander(f"📚 Nguồn trích dẫn ({len(sources)})"):
                            show_sources(sources)

        question = st.chat_input("Nhập câu hỏi của bạn về tài liệu đã chọn...")

        if question:
            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):
                with st.spinner("Agent Harness đang suy luận và tìm kiếm tri thức..."):
                    chat_res = api_request(
                        api_url,
                        "POST",
                        "/chat",
                        token=token,
                        json={
                            "question": question,
                            "conversation_id": conversation_id,
                            "document_ids": selected_documents,
                            "remember": remember_toggle,
                        },
                    )

                    if chat_res and chat_res.status_code == 200:
                        data = chat_res.json()
                        st.markdown(data["answer"])

                        if data.get("sources"):
                            with st.expander(f"📚 Nguồn trích dẫn ({len(data['sources'])})"):
                                show_sources(data["sources"])

                        memory_info = data.get("memory", {})
                        if memory_info.get("conflicts", 0) > 0:
                            st.warning(
                                f"⚠️ Phát hiện {memory_info['conflicts']} thông tin mâu thuẫn với bộ nhớ cũ! "
                                "Vui lòng chuyển sang tab 'Quản lý Bộ nhớ' để xác nhận."
                            )

                        if memory_info.get("status") == "failed":
                            st.info("Câu trả lời đã lưu, nhưng quá trình cập nhật bộ nhớ gặp trục trặc.")

                        with st.expander("🔍 Chi tiết quan sát (Observability / Trace)"):
                            st.caption(f"Trace ID: `{data.get('trace_id')}`")
                            st.json(data.get("trace", []))
                    elif chat_res:
                        detail = chat_res.json().get("detail", chat_res.text)
                        st.error(f"Xử lý thất bại (HTTP {chat_res.status_code}): {detail}")

    with memory_tab:
        st.subheader("Trí nhớ dài hạn cá nhân (Long-term Memory)")
        st.caption(
            "Bộ nhớ lưu trữ các thông tin và sở thích người dùng xuyên suốt các phiên hội thoại. "
            "Mọi mâu thuẫn thông tin phải được bạn xác nhận trước khi cập nhật."
        )

        mem_res = api_request(api_url, "GET", "/memories", token=token)
        memories = mem_res.json() if (mem_res and mem_res.status_code == 200) else []

        if not memories:
            st.info("Chưa có thông tin nào được lưu trong bộ nhớ.")
        else:
            for mem in memories:
                st.markdown(f"**🔑 {mem['key']}**: `{mem['value']}` (Phiên bản: v{mem['version']})")

                # Check for conflict
                if mem.get("pending_value"):
                    st.warning(
                        f"⚠️ **Xung đột bộ nhớ:** Phát hiện thông tin mới: `{mem['pending_value']}`. "
                        "Bạn muốn giữ thông tin cũ hay dùng thông tin mới?"
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Dùng thông tin mới", key=f"acc_{mem['id']}"):
                            resolve_res = api_request(
                                api_url,
                                "POST",
                                f"/memories/{mem['id']}/resolve",
                                token=token,
                                json={"accept": True},
                            )
                            if resolve_res and resolve_res.status_code == 200:
                                st.success("Đã cập nhật thông tin mới!")
                                st.rerun()
                    with col2:
                        if st.button("❌ Giữ thông tin cũ", key=f"rej_{mem['id']}"):
                            resolve_res = api_request(
                                api_url,
                                "POST",
                                f"/memories/{mem['id']}/resolve",
                                token=token,
                                json={"accept": False},
                            )
                            if resolve_res and resolve_res.status_code == 200:
                                st.info("Đã giữ lại thông tin cũ.")
                                st.rerun()

                if st.button("🗑️ Quên thông tin này", key=f"del_mem_{mem['id']}"):
                    del_res = api_request(api_url, "DELETE", f"/memories/{mem['id']}", token=token)
                    if del_res and del_res.status_code == 200:
                        st.success("Đã xóa khỏi bộ nhớ!")
                        st.rerun()

                st.divider()


if __name__ == "__main__":
    main()
