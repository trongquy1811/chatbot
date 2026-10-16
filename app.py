import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import streamlit as st
from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Agent Harness Chatbot",
    page_icon="🤖",
    layout="wide",
)


def local_config():
    return dotenv_values(
        PROJECT_ROOT / ".env",
        encoding="utf-8-sig",
        interpolate=False,
    )


def is_local_url(url):
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


def default_local_token(api_url):
    """Chỉ tự điền token khi bật chế độ local và gọi backend local."""
    config = local_config()
    enabled = os.getenv(
        "LOCAL_AUTO_LOGIN",
        config.get("LOCAL_AUTO_LOGIN") or "false",
    ).lower() in {"true", "1", "yes"}

    if not enabled or not is_local_url(api_url):
        return ""

    raw = os.getenv(
        "API_KEYS_JSON",
        config.get("API_KEYS_JSON") or "{}",
    )

    try:
        tokens = json.loads(raw)
        if isinstance(tokens, dict):
            return next(
                (
                    token
                    for token in tokens
                    if isinstance(token, str) and len(token) >= 24
                ),
                "",
            )
    except (TypeError, ValueError):
        pass

    return ""


def error_detail(response):
    try:
        payload = response.json()
    except ValueError:
        return f"Backend trả về HTTP {response.status_code}."

    detail = (
        payload.get("detail", payload)
        if isinstance(payload, dict)
        else payload
    )

    if isinstance(detail, dict):
        message = detail.get("message", "Yêu cầu thất bại.")
        trace_id = detail.get("trace_id")
        if trace_id:
            message += f"\n\nTrace ID: {trace_id}"
        return message

    if isinstance(detail, list):
        return "Dữ liệu gửi lên không hợp lệ. Kiểm tra các trường nhập."

    return str(detail)


def request_api(api_url, token, method, route, **kwargs):
    timeout = 300 if route in {"/documents", "/chat"} and method == "POST" else 20

    try:
        response = httpx.request(
            method,
            api_url + route,
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(timeout, connect=5),
            # Tránh proxy hệ thống can thiệp kết nối localhost.
            trust_env=not is_local_url(api_url),
            follow_redirects=False,
            **kwargs,
        )
    except httpx.TimeoutException:
        st.error(
            "Backend phản hồi quá thời gian chờ. "
            "Kiểm tra terminal backend trước khi gửi lại; "
            "yêu cầu trước có thể vẫn đang xử lý."
        )
        st.stop()
    except httpx.RequestError:
        st.error(
            f"Không kết nối được backend tại {api_url}. "
            "Kiểm tra backend đang chạy và đúng cổng."
        )
        st.stop()

    if response.status_code == 401:
        st.error(
            "Access token không hợp lệ. Kiểm tra API_KEYS_JSON "
            "và khởi động lại backend sau khi đổi .env."
        )
        st.stop()

    if not response.is_success:
        st.error(
            f"Yêu cầu thất bại (HTTP {response.status_code}): "
            f"{error_detail(response)}"
        )
        st.stop()

    if response.status_code == 204:
        return None

    try:
        return response.json()
    except ValueError:
        st.error("Backend trả về dữ liệu không đúng định dạng JSON.")
        st.stop()


def show_sources(sources):
    if not sources:
        st.info("Không có nguồn trích dẫn được trả về.")
        return

    for source in sources:
        st.write(
            f"📄 {source.get('name', 'Tài liệu')} "
            f"· trang {source.get('page', '?')}"
        )
        st.caption(f"Source ID: {source.get('id', '')}")
        st.write(source.get("excerpt", ""))
        st.divider()


def flash(message):
    st.session_state["notice"] = message
    st.rerun()


def main():
    st.title("🤖 Agent Harness Chatbot")
    st.caption("Hỏi đáp tài liệu · Nguồn trích dẫn · Bộ nhớ hội thoại")

    config = local_config()
    default_url = os.getenv(
        "API_BASE_URL",
        config.get("API_BASE_URL") or "http://127.0.0.1:8000",
    )

    with st.sidebar:
        st.header("⚙️ Kết nối & Xác thực")

        api_url = st.text_input(
            "Backend API URL",
            value=default_url,
        ).strip().rstrip("/")

        try:
            parsed = urlsplit(api_url)
            valid_url = (
                parsed.scheme in {"http", "https"}
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and not parsed.query
                and not parsed.fragment
            )
        except ValueError:
            valid_url = False

        if not valid_url:
            st.warning("Nhập URL hợp lệ, ví dụ http://127.0.0.1:8000.")
            st.stop()

        # Xóa token trên giao diện khi chuyển sang backend khác.
        if st.session_state.get("token_backend_url") != api_url:
            st.session_state["token_backend_url"] = api_url
            st.session_state.pop("access_token_input", None)

        if not st.session_state.get("access_token_input"):
            config = local_config()
            try:
                tokens = json.loads(config.get("API_KEYS_JSON") or "{}")
                saved_token = (
                    next(iter(tokens), "")
                    if isinstance(tokens, dict)
                    else ""
                )
            except (ValueError, TypeError):
                saved_token = ""

            st.session_state["access_token_input"] = (
                saved_token if is_local_url(api_url) else ""
            )

        token = st.text_input(
            "Access token",
            type="password",
            key="access_token_input",
            help="Tự điền token từ file .env khi chạy local.",
        ).strip()

        if st.button("Đọc lại token local"):
            st.session_state["reload_local_token"] = True
            st.rerun()

        if st.session_state.pop("reload_local_token", False):
            # Cập nhật widget ở lần chạy kế tiếp.
            st.session_state.pop("access_token_input", None)
            st.rerun()

        if not token:
            st.info("Nhập Access token để tiếp tục.")
            st.stop()

        # Khi đổi backend hoặc token, xóa lựa chọn của tài khoản trước.
        identity = (api_url, token)
        if st.session_state.get("current_identity") != identity:
            for key in (
                "conversation_picker",
                "document_picker",
                "uploaded_document",
                "notice",
            ):
                st.session_state.pop(key, None)
            st.session_state["current_identity"] = identity

        auth = request_api(api_url, token, "GET", "/auth/verify")
        st.success(f"Đã đăng nhập: {auth.get('owner', 'Người dùng')}")

    def api(method, route, **kwargs):
        return request_api(api_url, token, method, route, **kwargs)

    if notice := st.session_state.pop("notice", None):
        st.success(notice)

    # Chỉ lấy dữ liệu sau khi xác thực thành công.
    documents = api("GET", "/documents")
    conversations = api("GET", "/conversations")

    with st.sidebar:
        st.divider()
        st.header("📁 Tài liệu")

        uploaded = st.file_uploader(
            "Tải tài liệu tham khảo",
            type=["pdf", "txt", "md", "markdown", "png", "jpg", "jpeg"],
            key="uploaded_document",
        )

        analyze_images = st.checkbox(
            "Phân tích toàn bộ hình ảnh trong PDF",
            value=False,
            help="Bật khi cần đọc biểu đồ hoặc hình ảnh; có thể xử lý lâu hơn.",
        )

        if st.button("📤 Tải lên & Xử lý", disabled=uploaded is None):
            with st.spinner("Đang đọc và lập chỉ mục tài liệu…"):
                api(
                    "POST",
                    "/documents",
                    params={"analyze_all_images": analyze_images},
                    files={
                        "file": (
                            uploaded.name,
                            uploaded.getvalue(),
                            uploaded.type or "application/octet-stream",
                        )
                    },
                )
            flash("Đã xử lý tài liệu.")

        ready_docs = {
            document["id"]: document
            for document in documents
            if document["status"] == "ready"
        }

        # Loại lựa chọn đã bị xóa hoặc không còn sẵn sàng.
        if "document_picker" in st.session_state:
            st.session_state["document_picker"] = [
                item
                for item in st.session_state["document_picker"]
                if item in ready_docs
            ]

        selected_documents = st.multiselect(
            "Tài liệu dùng cho câu hỏi",
            options=list(ready_docs),
            format_func=lambda item: ready_docs[item]["name"],
            key="document_picker",
        )

        with st.expander(f"Danh sách tài liệu ({len(documents)})"):
            for document in documents:
                st.write(
                    f"{document['name']} · {document['status']} "
                    f"· {document.get('chunks', 0)} chunks"
                )
                if st.button(
                    "Xóa tài liệu",
                    key=f"delete_document_{document['id']}",
                ):
                    api("DELETE", f"/documents/{document['id']}")
                    flash("Đã xóa tài liệu.")

        st.divider()
        st.header("💬 Hội thoại")

        if st.button("➕ Hội thoại mới"):
            conversation = api(
                "POST",
                "/conversations",
                json={"title": "Hội thoại mới"},
            )
            st.session_state["conversation_picker"] = conversation["id"]
            st.rerun()

        if not conversations:
            conversation = api(
                "POST",
                "/conversations",
                json={"title": "Hội thoại đầu tiên"},
            )
            st.session_state["conversation_picker"] = conversation["id"]
            st.rerun()

        lookup = {
            conversation["id"]: conversation["title"]
            for conversation in conversations
        }

        if st.session_state.get("conversation_picker") not in lookup:
            st.session_state["conversation_picker"] = next(iter(lookup))

        conversation_id = st.selectbox(
            "Chọn hội thoại",
            options=list(lookup),
            format_func=lambda item: f"{lookup[item]} ({item[:6]})",
            key="conversation_picker",
        )

        remember = st.checkbox(
            "Cho phép ghi nhớ thông tin tôi yêu cầu lưu",
            value=False,
            help=(
                "Thông tin cá nhân mâu thuẫn cần được xác nhận "
                "trong tab Bộ nhớ."
            ),
        )

    chat_tab, memory_tab = st.tabs(["💬 Hỏi đáp", "🧠 Bộ nhớ"])

    with chat_tab:
        history = api(
            "GET",
            f"/conversations/{conversation_id}/messages",
        )

        for message in history:
            role = message.get("role", "assistant")
            if role not in {"user", "assistant"}:
                role = "assistant"

            with st.chat_message(role):
                st.markdown(message.get("content", ""))
                if message.get("sources"):
                    with st.expander("Nguồn trích dẫn"):
                        show_sources(message["sources"])

        if not selected_documents:
            st.caption(
                "Chọn tài liệu ở thanh bên để hỏi về nội dung tài liệu."
            )

        question = st.chat_input("Nhập câu hỏi…")

        if question and question.strip():
            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):
                with st.spinner("Đang tìm kiếm và trả lời…"):
                    result = api(
                        "POST",
                        "/chat",
                        json={
                            "question": question.strip(),
                            "conversation_id": conversation_id,
                            "document_ids": selected_documents,
                            "remember": remember,
                        },
                    )

                st.markdown(result["answer"])

                if result.get("sources"):
                    with st.expander("Nguồn trích dẫn"):
                        show_sources(result["sources"])

                memory_info = result.get("memory") or {}
                if memory_info.get("conflicts"):
                    st.warning(
                        "Có thông tin bộ nhớ mâu thuẫn. "
                        "Mở tab Bộ nhớ để xác nhận."
                    )

                if memory_info.get("status") == "failed":
                    st.warning(
                        "Câu trả lời đã lưu nhưng cập nhật bộ nhớ thất bại."
                    )

                with st.expander("Chi tiết xử lý"):
                    st.caption(f"Trace ID: {result.get('trace_id', '')}")
                    st.json(result.get("trace", []))

    with memory_tab:
        st.subheader("Bộ nhớ cá nhân")
        st.caption(
            "Thông tin mâu thuẫn chỉ thay thế bộ nhớ cũ sau khi bạn xác nhận."
        )

        memories = api("GET", "/memories")
        if not memories:
            st.info("Chưa có thông tin được ghi nhớ.")

        for memory in memories:
            st.write(
                f"{memory['key']}: {memory['value']} "
                f"· phiên bản {memory.get('version', 1)}"
            )

            if memory.get("pending_value") is not None:
                st.warning(f"Thông tin mới: {memory['pending_value']}")
                accept_column, reject_column = st.columns(2)

                if accept_column.button(
                    "Dùng thông tin mới",
                    key=f"accept_memory_{memory['id']}",
                ):
                    api(
                        "POST",
                        f"/memories/{memory['id']}/resolve",
                        json={"accept": True},
                    )
                    flash("Đã chấp nhận thông tin mới.")

                if reject_column.button(
                    "Giữ thông tin cũ",
                    key=f"reject_memory_{memory['id']}",
                ):
                    api(
                        "POST",
                        f"/memories/{memory['id']}/resolve",
                        json={"accept": False},
                    )
                    flash("Đã giữ thông tin cũ.")

            if st.button(
                "Quên thông tin này",
                key=f"delete_memory_{memory['id']}",
            ):
                api("DELETE", f"/memories/{memory['id']}")
                flash("Đã xóa bộ nhớ.")

            st.divider()


if __name__ == "__main__":
    main()