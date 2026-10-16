
from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

replacements = {
    'st.title("?? Agent Harness Chatbot")':
        'st.title("\\U0001F916 Agent Harness Chatbot")',

    '"Ki?n tr?c Agent Harness ? Gemini LLM ? Qdrant Vector Search ? Redis Cache ? PostgreSQL Memory"':
        '"Kiến trúc Agent Harness · Gemini LLM · Qdrant Vector Search · Redis Cache · PostgreSQL Memory"',

    '"Vui lÃ²ng kiá»ƒm tra láº¡i dá»‹ch vá»¥ backend."':
        '"Vui lòng kiểm tra lại dịch vụ backend."',

    'st.header("ðŸ”£ xÃ¡c thá»±c: **{st.session_state.auth_user}**")':
        'st.header(f"🔐 Xác thực: **{st.session_state.auth_user}**")',

    '"Agent Harness Ä‘ang suy luáº­n vÃ  tÃ¬m kiáº¿m tri thá»©c..."':
        '"Agent Harness đang suy luận và tìm kiếm tri thức..."',

    '"Vui lÃ²ng chuyá»ƒn sang tab \'Quáº£n lÃ½ Bá»™ nhá»›\' Ä‘á»ƒ xÃ¡c nháº­n."':
        '"Vui lòng chuyển sang tab \'Quản lý Bộ nhớ\' để xác nhận."',
}

for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
        print("Đã sửa:", old[:55])
    else:
        print("Không tìm thấy:", old[:55])

path.write_text(text, encoding="utf-8")
print("Hoàn tất. app.py đã được lưu bằng UTF-8.")
