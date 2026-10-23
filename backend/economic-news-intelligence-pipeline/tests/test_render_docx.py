from unittest import TestCase

try:
    from src.render_docx import _summary_text
    DOCX_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    _summary_text = None
    DOCX_IMPORT_ERROR = exc


class RenderDocxSummaryTests(TestCase):
    def setUp(self) -> None:
        if DOCX_IMPORT_ERROR is not None:
            self.skipTest(f"python-docx unavailable: {DOCX_IMPORT_ERROR}")

    def test_only_llm_summary_is_rendered(self) -> None:
        item = {
            "summary_zh": "这是 LLM 生成的中文摘要。",
            "summary_source": "llm",
            "summary": "raw source summary",
            "raw_snippet": "raw snippet",
        }
        self.assertEqual(_summary_text(item), "这是 LLM 生成的中文摘要。")

    def test_non_llm_fallback_summary_is_left_blank(self) -> None:
        item = {
            "summary_zh": "",
            "summary_source": "none",
            "summary": "raw source summary",
            "raw_snippet": "raw snippet",
            "raw_description": "raw description",
        }
        self.assertEqual(_summary_text(item), "")
