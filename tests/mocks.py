from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from backend.schemas import Fact

TEST_TOKEN = "valid_test_token_1234567890abcdef"
TEST_USER = "test_user"


class MockEmbeddings:
    """Mock embeddings generating deterministic 4-dimensional vector."""
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3, 0.4]


class MockGemini:
    """Mock Gemini provider for isolated unit and integration testing."""
    def __init__(self):
        self.embeddings = MockEmbeddings()
        self.llm = MagicMock()
        mock_response = AIMessage(
            content="Đây là câu trả lời thử nghiệm từ tài liệu [source:test_chunk_1]."
        )
        self.llm.invoke.return_value = mock_response
        self.llm.bind_tools.return_value = self.llm
        self.llm.with_structured_output.return_value = MagicMock(
            invoke=lambda _: MagicMock(facts=[Fact(key="user.name", value="Nguyen Van A")])
        )

    def vision(self, content: bytes, mime: str) -> str:
        return "Nội dung hình ảnh thử nghiệm mô tả biểu đồ doanh thu."

    def extract_facts(self, content: str, personal: bool = False) -> list[Fact]:
        if personal:
            return [Fact(key="user.favorite_language", value="Python")]
        return [Fact(key="project.name", value="DocAnalyzer")]
