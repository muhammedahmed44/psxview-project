from unittest import TestCase

from src.summary import _has_summary_context, _normalize_generated_summary, validate_summary_zh


class SummaryValidationTests(TestCase):
    def test_normalize_generated_summary_strips_labels(self) -> None:
        raw = "标题：美国7月CPI回落。摘要：通胀降温带动降息预期升温。"
        self.assertEqual(
            _normalize_generated_summary(raw),
            "美国7月CPI回落。通胀降温带动降息预期升温。",
        )

    def test_repeated_macro_terms_are_allowed(self) -> None:
        verdict = validate_summary_zh(
            "美国7月通胀回落，市场对美联储降息预期升温。这反映出美国经济和金融市场正在重新定价后续政策路径。",
            {"original_source": "NPR", "source": "NPR"},
        )
        self.assertEqual(verdict, "ok")

    def test_source_name_subject_still_blocked_for_non_whitelist_source(self) -> None:
        verdict = validate_summary_zh(
            "中国经济网报道称，全球贸易规模扩张基础不稳，外需修复仍存在不确定性。",
            {"original_source": "中国经济网", "source": "中国经济网"},
        )
        self.assertEqual(verdict, "source_name_as_subject")

    def test_title_only_context_is_not_enough_for_summary(self) -> None:
        item = {
            "title": "美国7月CPI回落",
            "raw_title": "美国7月CPI回落",
            "raw_description": "美国7月CPI回落",
            "raw_snippet": "",
            "meta_description": "",
            "summary": "",
        }
        self.assertFalse(_has_summary_context(item))

    def test_list_like_output_is_rejected(self) -> None:
        verdict = validate_summary_zh(
            "1. 美国7月CPI回落。2. 市场对降息预期升温。",
            {"original_source": "NPR", "source": "NPR"},
        )
        self.assertEqual(verdict, "list_like_output")
