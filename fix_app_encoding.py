
from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

replacements = {
    "??": "🤖",
    "ðŸ” XÃ¡c thá»±c ngÆ°á»i dÃ¹ng": "🔐 Xác thực người dùng",
    "Nháº­p Access Token": "Nhập Access Token",
    "Access Token (tá»‘i thiá»ƒu 24 kÃ½ tá»±) Ä‘Æ°á»£c cáº¥u hÃ¬nh trong há»‡ thá»‘ng.": "Access Token (tối thiểu 24 ký tự) được cấu hình trong hệ thống.",
    "Vui lÃ²ng nháº­p Access Token Ä‘á»ƒ truy cáº­p há»‡ thá»‘ng.": "Vui lòng nhập Access Token để truy cập hệ thống.",
    "âŒ Access Token khÃ´ng há»£p lá»‡ hoáº·c Ä‘Ã£ bá»‹ vÃ´ hiá»‡u hÃ³a.": "❌ Access Token không hợp lệ hoặc đã bị vô hiệu hóa.",
    "ÄÃ£ xÃ¡c thá»±c: **{st.session_state.auth_user}**": "Đã xác thực: **{st.session_state.auth_user}**",
    "ðŸ“ Quáº£n lÃ½ TÃ i liá»‡u": "📁 Quản lý Tài liệu",
    "Táº£i tÃ i liá»‡u tham kháº£o": "Tải tài liệu tham khảo",
    "PhÃ¢n tÃ­ch toÃ n bá»™ hÃ¬nh áº£nh trong PDF (OCR)": "Phân tích toàn bộ hình ảnh trong PDF (OCR)",
    "ðŸ“¤ Táº£i lÃªn & Xá»­ lÃ½": "📤 Tải lên & Xử lý",
    "ðŸ’¬ Há»™i thoáº¡i": "💬 Hội thoại",
    "ðŸ§  Cho phÃ©p ghi nhá»› thÃ´ng tin (Memory)": "🧠 Cho phép ghi nhớ thông tin (Memory)",
    "ðŸ’¬ Há»i Ä‘Ã¡p RAG": "💬 Hỏi đáp RAG",
    "ðŸ§  Quáº£n lÃ½ Bá»™ nhá»›": "🧠 Quản lý Bộ nhớ",
    "Tr\\u00ed nh\\u1edb d\\u00e0i h\\u1ea1n c\\u00e1 nh\\u00e2n": "Trí nhớ dài hạn cá nhân",
    "ChÆ°a cÃ³ thÃ´ng tin nÃ o Ä‘Æ°á»£c lÆ°u trong bá»™ nhá»›.": "Chưa có thông tin nào được lưu trong bộ nhớ.",
    "ðŸ”‘": "🔑",
    "PhiÃªn báº£n": "Phiên bản",
    "âš ï¸": "⚠️",
    "âœ… DÃ¹ng thÃ´ng tin má»›i": "✅ Dùng thông tin mới",
    "ÄÃ£ cáº­p nháº­t thÃ´ng tin má»›i!": "Đã cập nhật thông tin mới!",
    "âŒ Giá»¯ thÃ´ng tin cÅ©": "❌ Giữ thông tin cũ",
    "ÄÃ£ giá»¯ láº¡i thÃ´ng tin cÅ©.": "Đã giữ lại thông tin cũ.",
    "ðŸ—‘ï¸ QuÃªn thÃ´ng tin nÃ y": "🗑️ Quên thông tin này",
    "ÄÃ£ xÃ³a khá»i bá»™ nhá»›!": "Đã xóa khỏi bộ nhớ!",
}

for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("Đã lưu app.py bằng UTF-8.")
