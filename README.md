# 🤖 Agent Harness Document AI Chatbot

Hệ thống AI Agent thông minh xây dựng trên nền tảng **Agent Harness Architecture**, kết hợp Mô hình ngôn ngữ lớn (**LLM**) cùng hạ tầng bao bọc (**Harness**) cung cấp các khả năng: **Tools**, **Memory**, **Execution Environment**, **Guardrails**, và **Observability**.

---

## 🛠️ KIẾN TRÚC VÀ CÔNG NGHỆ HỆ THỐNG

```
                            +-----------------------------------------------+
                            |                    HARNESS                    |
                            |                                               |
+-------------------+       |  +--------------------+  +-----------------+  |
| 1. Tools          |<======+==|   FastAPI Backend  |  | 2. Memory       |  |
| - search_documents|       |  |   (Async REST API) |  | - Qdrant Vector |  |
| - extract_facts   |       |  +---------+----------+  | - Redis State   |  |
+-------------------+       |            |             | - Postgres Truth|  |
                            |            v             +-----------------+  |
+-------------------+       |  +--------------------+                       |
| 4. Guardrails     |=======>==|   LLM CORE ENGINE  |                       |
| - Anti-Injection  |       |  |   (Gemini 2.5 Flash|                       |
| - Citation Check  |       |  |    + Embeddings)   |                       |
| - Timeout & Limits|       |  +---------+----------+                       |
+-------------------+       |            |             +-----------------+  |
                            |            v             | 3. Môi trường   |  |
                            |  +--------------------+  | - Docker        |  |
                            |  | 5. Observability   |  | - Fly.io        |  |
                            |  | - Trace ID, Latency|  | - LangGraph Run |  |
                            |  | - Redact Secret Log|  +-----------------+  |
                            |  +--------------------+                       |
                            +-----------------------------------------------+
```

1. **Generative AI & Memory (Bộ nhớ & Tìm kiếm):**
   - **Google Gemini (gemini-2.5-flash):** Đóng vai trò là hạt nhân suy luận trung tâm, xử lý ngữ cảnh và trích xuất facts.
   - **Gemini Embeddings (gemini-embedding-001):** Vector hóa tài liệu và bộ nhớ dài hạn.
   - **Qdrant:** Cơ sở dữ liệu vector chuyên dụng, thực hiện **Semantic Search** và truy xuất tri thức dài hạn (**Long-term Memory**).
   - **Redis:** Quản lý bộ đệm tìm kiếm (**Retrieval Cache**) và trạng thái phiên làm việc ngắn hạn (**State & Short-term Memory**). Tự động fallback sang PostgreSQL khi Redis gặp sự cố.
2. **Backend & Deployment (API & Vận hành):**
   - **FastAPI:** Khung ứng dụng REST API bất đồng bộ hiệu năng cao, kiểm soát quyền truy cập chặt chẽ.
   - **Docker & Docker Compose:** Đóng gói container chuẩn hóa toàn bộ các dịch vụ (API, UI, PostgreSQL, Qdrant, Redis).
   - **Fly.io:** Cấu hình triển khai cloud production tách biệt cho Backend (`fly.toml`) và Giao diện (`fly.ui.toml`).
3. **Database & Testing:**
   - **PostgreSQL:** Cơ sở dữ liệu quan hệ lưu trữ dữ liệu gốc (*Single Source of Truth*): thông tin người dùng, tài liệu, lịch sử hội thoại và các phiên bản bộ nhớ.
   - **Streamlit:** Giao diện người dùng trực quan, tích hợp cổng đăng nhập bảo mật và quản trị bộ nhớ tương tác.
   - **pytest:** Hệ thống kiểm thử tự động toàn diện (Unit & Integration tests).
   - **GitHub Actions:** Tự động hóa kiểm thử liên tục (CI).

---

## 📂 CẤU TRÚC DỰ ÁN

```
chatbot/
├── app.py                      # Giao diện Streamlit (Xác thực, Hỏi đáp RAG, Quản lý Bộ nhớ)
├── requirements.txt            # Thư viện Python phụ thuộc
├── .env.example                # Mẫu cấu hình môi trường chuẩn
├── .env                        # File cấu hình riêng (được bảo vệ bởi .gitignore)
├── .gitignore                  # Ngăn chặn rò rỉ khóa, thư mục ảo và dữ liệu tải lên
├── .dockerignore               # Tối ưu kích thước container build
├── Dockerfile                  # Đóng gói backend FastAPI & giao diện Streamlit
├── compose.yaml                # Cấu hình đa dịch vụ: API, UI, PostgreSQL, Redis, Qdrant
├── fly.toml                    # Cấu hình triển khai Backend lên Fly.io
├── fly.ui.toml                 # Cấu hình triển khai UI Streamlit lên Fly.io
├── pytest.ini                  # Cấu hình môi trường chạy kiểm thử pytest
├── README.md                   # Tài liệu hướng dẫn chi tiết
│
├── backend/                    # Mã nguồn hạt nhân Backend
│   ├── __init__.py
│   ├── main.py                 # Khởi tạo FastAPI, quản lý Lifespan, Health checks
│   ├── config.py               # Đọc và xác thực cấu hình qua Pydantic Settings
│   ├── auth.py                 # Xác thực Bearer Token bảo mật (constant-time check)
│   ├── database.py             # Kết nối PostgreSQL / SQLite engine & session factory
│   ├── models.py               # Bảng SQLAlchemy (Document, Conversation, Message, Memory)
│   ├── schemas.py              # Schema Pydantic kiểm tra request & response
│   │
│   ├── api/                    # Các Router API
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependencies (Khóa độc quyền ghi, kiểm tra quyền sở hữu)
│   │   ├── documents.py        # Tải lên, phân tích chunk, lập chỉ mục và xóa tài liệu
│   │   ├── conversations.py    # Quản lý cuộc hội thoại và lịch sử tin nhắn
│   │   ├── chat.py             # Endpoint hỏi đáp chính gọi Agent Harness
│   │   └── memories.py         # Quản trị bộ nhớ dài hạn, giải quyết xung đột thông tin
│   │
│   ├── agent/                  # Thành phần trí tuệ nhân tạo (LangGraph Agent)
│   │   ├── __init__.py
│   │   ├── prompts.py          # System prompt định nghĩa vai trò & quy tắc Harness
│   │   ├── state.py            # Khai báo schema trạng thái LangGraph
│   │   ├── tools.py            # Công cụ tìm kiếm ngữ nghĩa và trích xuất facts
│   │   ├── graph.py            # Đồ thị StateGraph suy luận vòng lặp có kiểm soát
│   │   └── guardrails.py       # Hàng rào bảo vệ (Anti-Prompt Injection, Citation Verification)
│   │
│   └── services/               # Các tầng dịch vụ chuyên biệt
│       ├── __init__.py
│       ├── gemini.py           # Kết nối Gemini LLM, Embeddings, Multimodal Vision
│       ├── ingestion.py        # Đọc PDF, Text, Markdown, Image OCR và chia chunks
│       ├── vectors.py          # Qdrant client: Semantic search tài liệu & bộ nhớ vector
│       ├── cache.py            # Redis Cache kết quả tìm kiếm ngữ nghĩa
│       ├── sessions.py         # Quản lý context ngắn hạn (Redis cache + PostgreSQL fallback)
│       ├── facts.py            # Trích xuất sự thật có cấu trúc qua Structured Output
│       ├── memory.py           # Hợp nhất bộ nhớ, theo dõi phiên bản và phát hiện xung đột
│       └── observability.py    # Ghi nhận log, Trace ID, đo lường thời gian không lộ bí mật
│
├── tests/                      # Bộ kiểm thử tự động toàn diện
│   ├── __init__.py
│   ├── conftest.py             # Fixture SQLite in-memory, mock LLM, Qdrant client
│   ├── mocks.py                # Lớp Mock Gemini, Mock Embeddings phục vụ test độc lập
│   ├── test_auth.py            # Kiểm thử xác thực token và từ chối 401
│   ├── test_documents.py       # Kiểm thử tải lên, kiểm tra định dạng và xóa tài liệu
│   ├── test_retrieval.py       # Kiểm thử vector search và khả năng chịu lỗi của Cache
│   ├── test_memory.py          # Kiểm thử logic mâu thuẫn bộ nhớ, giải quyết và revision
│   └── test_agent.py           # Kiểm thử luồng LangGraph Agent và hàng rào bảo vệ
│
└── .github/
    └── workflows/
        └── ci.yml              # Quy trình CI tự động chạy pytest trên GitHub Actions
```

---

## 📋 QUY TRÌNH HOẠT ĐỘNG 6 BƯỚC

1. **Đăng nhập:** Người dùng nhập Access token tại giao diện. Hệ thống xác thực token qua endpoint `/auth/verify` thành công trước khi hiển thị bất kỳ tính năng nào khác. Không bao giờ tắt xác thực để né lỗi 401.
2. **Nhập tài liệu:** Kiểm tra định dạng (PDF, TXT, MD, PNG, JPG), giới hạn kích thước -> trích xuất nội dung văn bản (kèm tùy chọn OCR hình ảnh) -> phân chia chunks -> tạo embeddings -> lưu trữ vector lên Qdrant và metadata lên PostgreSQL.
3. **Hỏi đáp RAG:** Xác thực request -> lấy ngữ cảnh hội thoại từ Redis (fallback về PostgreSQL nếu Redis lỗi) -> nạp bộ nhớ dài hạn liên quan -> LangGraph kích hoạt vòng lặp suy luận gọi công cụ tìm kiếm Qdrant -> Gemini trả lời kèm trích dẫn nguồn `[source:<source_id>]` được xác thực bởi Guardrails.
4. **Ghi nhớ (Memory):** Khi người dùng kích hoạt tùy chọn ghi nhớ (`remember=True`), hệ thống trích xuất facts có cấu trúc từ câu hỏi -> so sánh với bộ nhớ hiện có:
   - Nếu là thông tin mới: thêm vào bộ nhớ (phiên bản v1).
   - Nếu trùng khớp: giữ nguyên.
   - Nếu xuất hiện mâu thuẫn: **không ghi đè**, đưa vào trạng thái `pending_value` và gửi cảnh báo yêu cầu người dùng xác nhận ở tab Bộ nhớ.
5. **Đồng bộ bộ nhớ:** PostgreSQL giữ vai trò là dữ liệu chính (*Source of Truth*); Qdrant lập chỉ mục các bộ nhớ đã được xác nhận để phục vụ tìm kiếm ngữ nghĩa. Tuyệt đối không truy xuất bản ghi đã xóa hoặc chưa xác nhận.
6. **Theo dõi (Observability):** Mỗi yêu cầu được gán một `Trace ID` duy nhất, ghi lại thời gian xử lý từng chặng và trạng thái hoàn thành. Không bao giờ ghi API key, Access token hay nội dung bí mật vào log.

---

## 🔒 NGUYÊN TẮC CỐT LÕI CỦA BẢN MỚI

- **Tách biệt khóa:** Access token (xác thực người dùng) và Google Gemini API key (gọi mô hình AI) là hai khóa hoàn toàn độc lập.
- **Bảo mật tuyệt đối:** Không đưa `.env`, tài liệu người dùng tải lên hoặc môi trường Python lên GitHub.
- **Tối ưu OCR:** Chỉ đọc ảnh trong PDF khi người dùng yêu cầu phân tích toàn bộ ảnh, tiết kiệm chi phí và tăng tốc độ xử lý.
- **Khả năng chịu lỗi cao (Fault Tolerance):** Nếu Redis gặp sự cố, hệ thống tự động đọc lịch sử hội thoại trực tiếp từ PostgreSQL mà không làm gián đoạn người dùng.
- **Giới hạn an toàn (Harness Guardrails):** Cấu hình chặt chẽ thời gian chờ gọi AI (`llm_timeout`), số lần thử lại tối đa (`max_retries`), số vòng gọi công cụ (`max_tool_rounds`) và số lượng tool call trong mỗi vòng (tối đa 4).
- **Chống Prompt Injection:** Toàn bộ tài liệu và bộ nhớ được xem là dữ liệu tham khảo, tuyệt đối không cho phép ghi đè các chỉ dẫn điều khiển hệ thống.
- **Kiểm soát xung đột:** Mọi thông tin bộ nhớ mâu thuẫn bắt buộc phải được người dùng xác nhận trước khi thay thế.

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & CHẠY ỨNG DỤNG

### 1. Chuẩn bị môi trường & Cấu hình

Sao chép file cấu hình mẫu và điền các khóa cần thiết:

```bash
cp .env.example .env
```

Chỉnh sửa file `.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
API_KEYS_JSON={"my_secret_token_0123456789abcdef": "admin_user"}
```

### 2. Chạy toàn bộ hệ thống bằng Docker Compose (Khuyên dùng)

Chạy tất cả 5 dịch vụ (FastAPI, Streamlit UI, PostgreSQL, Redis, Qdrant) chỉ với 1 lệnh:

```bash
docker compose up -d --build
```

- **Backend API:** `http://localhost:8000/docs` (Swagger UI)
- **Frontend Streamlit:** `http://localhost:8501`

### 3. Chạy cục bộ (Local Development)

Nếu muốn chạy trực tiếp bằng môi trường Python local:

```bash
# 1. Cài đặt thư viện
pip install -r requirements.txt

# 2. Khởi chạy Backend API
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# 3. Khởi chạy Giao diện Streamlit (mở terminal mới)
streamlit run app.py
```

---

## 🧪 CHẠY KIỂM THỬ TỰ ĐỘNG (PYTEST)

Dự án đi kèm bộ kiểm thử tự động toàn diện, chạy độc lập mà không cần kết nối mạng hay khóa Gemini thật:

```bash
pytest tests/ -v
```

Kết quả kiểm thử:
```text
tests/test_agent.py::test_sanitize_reference_content PASSED              [  5%]
tests/test_agent.py::test_validate_citations PASSED                      [ 10%]
tests/test_agent.py::test_chat_endpoint_integration PASSED               [ 15%]
tests/test_agent.py::test_agent_run_execution PASSED                     [ 21%]
tests/test_auth.py::test_auth_missing_token PASSED                       [ 26%]
tests/test_auth.py::test_auth_invalid_token PASSED                       [ 31%]
tests/test_auth.py::test_auth_valid_token PASSED                         [ 36%]
tests/test_auth.py::test_protected_routes_require_auth PASSED            [ 42%]
tests/test_documents.py::test_upload_text_document PASSED                [ 47%]
tests/test_documents.py::test_list_documents PASSED                      [ 52%]
tests/test_documents.py::test_upload_empty_document PASSED               [ 57%]
tests/test_documents.py::test_upload_unsupported_format PASSED           [ 63%]
tests/test_documents.py::test_delete_document PASSED                     [ 68%]
tests/test_memory.py::test_memory_add_new_fact PASSED                    [ 73%]
tests/test_memory.py::test_memory_conflict_handling_and_resolution PASSED [ 78%]
tests/test_memory.py::test_delete_memory PASSED                          [ 84%]
tests/test_retrieval.py::test_vectors_add_and_search PASSED              [ 89%]
tests/test_retrieval.py::test_retrieval_cache_fallback PASSED            [ 94%]
tests/test_retrieval.py::test_retrieval_cache_redis_error_resilience PASSED [100%]
============================= 19 passed in 1.00s ==============================
```

---

## ☁️ TRIỂN KHAI LÊN CLOUD (FLY.IO)

Hệ thống đã chuẩn bị sẵn file cấu hình riêng biệt:

1. **Triển khai Backend API:**
   ```bash
   fly launch --config fly.toml
   fly secrets set GOOGLE_API_KEY="your_key" API_KEYS_JSON='{"token...": "user"}' DATABASE_URL="postgres://..."
   fly deploy --config fly.toml
   ```

2. **Triển khai Giao diện Streamlit:**
   ```bash
   fly launch --config fly.ui.toml
   fly secrets set API_BASE_URL="https://your-backend-app.fly.dev"
   fly deploy --config fly.ui.toml
   ```