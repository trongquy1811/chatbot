import os
import httpx
import streamlit as st

st.set_page_config(
    page_title="Agent Harness Chatbot",
    page_icon="🤖",
    layout="wide",
)

st.title("\U0001F916 Agent Harness Chatbot")
st.caption(
    "Kiến trúc Agent Harness · Gemini LLM · Qdrant Vector Search · Redis Cache · PostgreSQL Memory"
)

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8001",
).rstrip("/")


# Helper for API requests
def api_request(method: str, route: str, token: str | None = None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = httpx.request(
            method,
            f"{API_BASE_URL}{route}",
            headers=headers,
            timeout=120.0,
            **kwargs,
        )
        return response
    except httpx.RequestError as exc:
        st.error(
            f"KhÃ´ng thá»ƒ káº¿t ná»‘i Ä‘áº¿n Backend táº¡i `{API_BASE_URL}`: {exc}. "
            "Vui lòng kiểm tra lại dịch vụ backend."
        )
        st.stop()


def show_sources(sources: list[dict]):
    if not sources:
        st.info("KhÃ´ng cÃ³ tÃ i liá»‡u tham kháº£o nÃ o Ä‘Æ°á»£c trÃ­ch dáº«n.")
        return

    for source in sources:
        st.markdown(
            f"**ðŸ“„ {source.get('name', 'TÃ i liá»‡u')}** (Trang {source.get('page', 1)})"
        )
        st.caption(f"Source ID: `{source.get('id', '')}`")
        st.write(source.get("excerpt", ""))
        st.divider()


# ==========================================
# SIDEBAR: AUTHENTICATION
# ==========================================
with st.sidebar:
    st.header("🔐 Xác thực người dùng")
    token_input = st.text_input(
        "Nhập Access Token",
        type="password",
        help="Access Token (tối thiểu 24 ký tự) được cấu hình trong hệ thống.",
    )

    if st.session_state.get("auth_token") != token_input:
        st.session_state.auth_token = token_input
        st.session_state.auth_user = None
        for key in ["conversation_id", "document_picker"]:
            st.session_state.pop(key, None)

    # 1. ÄÄƒng nháº­p: kiá»ƒm tra Access token thÃ nh cÃ´ng trÆ°á»›c khi hiá»ƒn thá»‹ chá»©c nÄƒng
    if not token_input:
        st.warning("Vui lòng nhập Access Token để truy cập hệ thống.")
        st.stop()

    # Verify token against backend
    verify_res = api_request("GET", "/auth/verify", token=token_input)
    if verify_res.status_code == 401:
        st.error("❌ Access Token không hợp lệ hoặc đã bị vô hiệu hóa.")
        st.stop()
    elif verify_res.status_code != 200:
        st.error(f"Lá»—i kiá»ƒm tra xÃ¡c thá»±c (HTTP {verify_res.status_code}): {verify_res.text}")
        st.stop()

    auth_data = verify_res.json()
    st.session_state.auth_user = auth_data.get("owner", "Unknown")
    st.success(f"Đã xác thực: **{st.session_state.auth_user}**")

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
        help="Há»— trá»£ PDF, Text, Markdown vÃ  hÃ¬nh áº£nh (OCR tá»± Ä‘á»™ng).",
    )

    analyze_images = st.checkbox(
        "Phân tích toàn bộ hình ảnh trong PDF (OCR)",
        value=False,
        help="Báº­t tÃ¹y chá»n nÃ y náº¿u PDF chá»©a nhiá»u biá»ƒu Ä‘á»“ hoáº·c scan hÃ¬nh áº£nh.",
    )

    if st.button("📤 Tải lên & Xử lý", disabled=uploaded is None):
        with st.spinner("Äang trÃ­ch xuáº¥t ná»™i dung, chia chunk vÃ  láº­p chá»‰ má»¥c Qdrant..."):
            res = api_request(
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
            if res.status_code == 200:
                st.success("TÃ i liá»‡u Ä‘Ã£ Ä‘Æ°á»£c táº£i lÃªn vÃ  sáºµn sÃ ng!")
                st.rerun()
            else:
                detail = res.json().get("detail", res.text)
                st.error(f"Táº£i lÃªn tháº¥t báº¡i ({res.status_code}): {detail}")

    # Fetch documents list
    doc_res = api_request("GET", "/documents", token=token)
    documents = doc_res.json() if doc_res.status_code == 200 else []

    ready_docs = {d["id"]: d for d in documents if d["status"] == "ready"}

    selected_documents = st.multiselect(
        "Chá»n tÃ i liá»‡u cho cÃ¢u há»i:",
        options=list(ready_docs.keys()),
        format_func=lambda did: ready_docs[did]["name"],
        key="document_picker",
    )

    with st.expander(f"Danh sÃ¡ch tÃ i liá»‡u ({len(documents)})"):
        for doc in documents:
            status_badge = "âœ…" if doc["status"] == "ready" else "â³" if doc["status"] == "processing" else "âŒ"
            st.markdown(f"{status_badge} **{doc['name']}** ({doc['chunks']} chunks)")
            if st.button("ðŸ—‘ï¸ XÃ³a", key=f"del_doc_{doc['id']}"):
                del_res = api_request("DELETE", f"/documents/{doc['id']}", token=token)
                if del_res.status_code == 200:
                    st.session_state.pop("document_picker", None)
                    st.rerun()
                else:
                    st.error("KhÃ´ng thá»ƒ xÃ³a tÃ i liá»‡u.")

    st.divider()
    st.header("💬 Hội thoại")

    if st.button("âž• Há»™i thoáº¡i má»›i"):
        new_conv = api_request(
            "POST",
            "/conversations",
            token=token,
            json={"title": "Há»™i thoáº¡i má»›i"},
        )
        if new_conv.status_code == 200:
            st.session_state.conversation_id = new_conv.json()["id"]
            st.rerun()

    conv_res = api_request("GET", "/conversations", token=token)
    conversations = conv_res.json() if conv_res.status_code == 200 else []

    if not conversations:
        initial_conv = api_request(
            "POST",
            "/conversations",
            token=token,
            json={"title": "Há»™i thoáº¡i máº·c Ä‘á»‹nh"},
        )
        if initial_conv.status_code == 200:
            st.session_state.conversation_id = initial_conv.json()["id"]
            st.rerun()
        conversations = []

    conv_lookup = {c["id"]: c["title"] for c in conversations}
    conv_ids = list(conv_lookup.keys())

    curr_cid = st.session_state.get("conversation_id")
    sel_idx = conv_ids.index(curr_cid) if curr_cid in conv_ids else 0

    conversation_id = st.selectbox(
        "Chá»n cuá»™c há»™i thoáº¡i:",
        options=conv_ids,
        index=sel_idx if conv_ids else 0,
        format_func=lambda cid: f"{conv_lookup[cid]} ({cid[:6]})",
    )
    st.session_state.conversation_id = conversation_id

    st.divider()
    remember_toggle = st.checkbox(
        "🧠 Cho phép ghi nhớ thông tin (Memory)",
        value=False,
        help="Khi báº­t, AI sáº½ trÃ­ch xuáº¥t facts tá»« cÃ¢u há»i Ä‘á»ƒ lÆ°u vÃ o bá»™ nhá»› dÃ i háº¡n.",
    )


# ==========================================
# MAIN INTERFACE TABS
# ==========================================
chat_tab, memory_tab = st.tabs(["💬 Hỏi đáp RAG", "🧠 Quản lý Bộ nhớ"])

with chat_tab:
    # Load conversation history
    if conversation_id:
        msg_res = api_request(
            "GET",
            f"/conversations/{conversation_id}/messages",
            token=token,
        )
        history = msg_res.json() if msg_res.status_code == 200 else []

        for msg in history:
            role = msg["role"]
            content = msg["content"]
            sources = msg.get("sources", [])

            with st.chat_message(role):
                st.markdown(content)
                if sources:
                    with st.expander(f"ðŸ“š Nguá»“n trÃ­ch dáº«n ({len(sources)})"):
                        show_sources(sources)

    question = st.chat_input("Nháº­p cÃ¢u há»i cá»§a báº¡n vá» tÃ i liá»‡u Ä‘Ã£ chá»n...")

    if question:
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("Agent Harness Ä‘ang suy luáº­n vÃ  tÃ¬m kiáº¿m tri thá»©c..."):
                chat_res = api_request(
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

                if chat_res.status_code == 200:
                    data = chat_res.json()
                    st.markdown(data["answer"])

                    if data.get("sources"):
                        with st.expander(f"ðŸ“š Nguá»“n trÃ­ch dáº«n ({len(data['sources'])})"):
                            show_sources(data["sources"])

                    memory_info = data.get("memory", {})
                    if memory_info.get("conflicts", 0) > 0:
                        st.warning(
                            f"⚠️ PhÃ¡t hiá»‡n {memory_info['conflicts']} thÃ´ng tin mÃ¢u thuáº«n vá»›i bá»™ nhá»› cÅ©! "
                            "Vui lòng chuyển sang tab 'Quản lý Bộ nhớ' để xác nhận."
                        )

                    if memory_info.get("status") == "failed":
                        st.info("CÃ¢u tráº£ lá»i Ä‘Ã£ lÆ°u, nhÆ°ng quÃ¡ trÃ¬nh cáº­p nháº­t bá»™ nhá»› gáº·p trá»¥c tráº·c.")

                    with st.expander("ðŸ” Chi tiáº¿t quan sÃ¡t (Observability / Trace)"):
                        st.caption(f"Trace ID: `{data.get('trace_id')}`")
                        st.json(data.get("trace", []))
                else:
                    detail = chat_res.json().get("detail", chat_res.text)
                    st.error(f"Xá»­ lÃ½ tháº¥t báº¡i (HTTP {chat_res.status_code}): {detail}")


with memory_tab:
    st.subheader("Trí nhớ dài hạn cá nhân (Long-term Memory)")
    st.caption(
        "Bộ nhớ lưu trữ thông tin và sở thích. Những thông tin mâu thuẫn cần được bạn xác nhận trước khi cập nhật."
    )

    mem_res = api_request("GET", "/memories", token=token)
    memories = mem_res.json() if mem_res.status_code == 200 else []

    if not memories:
        st.info("Chưa có thông tin nào được lưu trong bộ nhớ.")
    else:
        for mem in memories:
            st.markdown(f"**🔑 {mem['key']}**: `{mem['value']}` (Phiên bản: v{mem['version']})")

            # Check for conflict
            if mem.get("pending_value"):
                st.warning(
                    f"⚠️ **Xung Ä‘á»™t bá»™ nhá»›:** PhÃ¡t hiá»‡n thÃ´ng tin má»›i: `{mem['pending_value']}`. "
                    "Báº¡n muá»‘n giá»¯ thÃ´ng tin cÅ© hay dÃ¹ng thÃ´ng tin má»›i?"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Dùng thông tin mới", key=f"acc_{mem['id']}"):
                        resolve_res = api_request(
                            "POST",
                            f"/memories/{mem['id']}/resolve",
                            token=token,
                            json={"accept": True},
                        )
                        if resolve_res.status_code == 200:
                            st.success("Đã cập nhật thông tin mới!")
                            st.rerun()
                with col2:
                    if st.button("❌ Giữ thông tin cũ", key=f"rej_{mem['id']}"):
                        resolve_res = api_request(
                            "POST",
                            f"/memories/{mem['id']}/resolve",
                            token=token,
                            json={"accept": False},
                        )
                        if resolve_res.status_code == 200:
                            st.info("Đã giữ lại thông tin cũ.")
                            st.rerun()

            if st.button("🗑️ Quên thông tin này", key=f"del_mem_{mem['id']}"):
                del_res = api_request("DELETE", f"/memories/{mem['id']}", token=token)
                if del_res.status_code == 200:
                    st.success("Đã xóa khỏi bộ nhớ!")
                    st.rerun()

            st.divider()
