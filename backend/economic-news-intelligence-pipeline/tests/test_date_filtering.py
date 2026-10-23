from __future__ import annotations

import unittest
from datetime import date

from src.quality import filter_quality_items_with_report


class DateFilteringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target_date = date(2026, 8, 9)
        self.config = {
            "watchlist_keywords": ("央行", "trade", "oil"),
            "thresholds": {"quality": {"min_quality_score": 2.0}},
            "allow_low_quality_sources": False,
        }

    def test_old_article_is_excluded(self) -> None:
        items = [{
            "title": "Trade ministry updates tariff policy",
            "summary": "New customs measures announced.",
            "url": "https://example.com/story",
            "published_date": "2026-08-08",
            "section": "domestic",
            "source_weight": 8,
            "source_quality": "official",
        }]
        retained, stats, _excluded = filter_quality_items_with_report(items, self.target_date, config=self.config)
        self.assertEqual(retained, [])
        self.assertEqual(stats.get("non_target_date"), 1)

    def test_missing_date_is_excluded(self) -> None:
        items = [{
            "title": "Central bank comments on liquidity",
            "summary": "Policy briefing.",
            "url": "https://example.com/story",
            "published_date": None,
            "section": "domestic",
            "source_weight": 8,
            "source_quality": "official",
        }]
        retained, stats, _excluded = filter_quality_items_with_report(items, self.target_date, config=self.config)
        self.assertEqual(retained, [])
        self.assertEqual(stats.get("missing_date"), 1)

    def test_possible_republished_old_story_is_excluded(self) -> None:
        items = [{
            "title": "Oil shipping disruption raises freight costs",
            "summary": "Freight markets react to new delays.",
            "url": "https://example.com/story",
            "published_date": "2026-08-09",
            "section": "international",
            "source_weight": 8,
            "source_quality": "tier1_media",
            "possible_republished_old_story": True,
        }]
        retained, stats, _excluded = filter_quality_items_with_report(items, self.target_date, config=self.config)
        self.assertEqual(retained, [])
        self.assertEqual(stats.get("possible_republished_old_story"), 1)

    def test_foreign_story_is_excluded_from_domestic_search_slot(self) -> None:
        items = [{
            "title": "US inflation cools as Treasury yields fall",
            "summary": "Federal Reserve expectations shift after CPI release.",
            "url": "https://example.com/intl-story",
            "published_date": "2026-08-09",
            "section": "domestic",
            "source_group": "google_topic",
            "source_weight": 8,
            "source_quality": "acceptable_media",
        }]
        retained, stats, _excluded = filter_quality_items_with_report(items, self.target_date, config=self.config)
        self.assertEqual(retained, [])
        self.assertEqual(stats.get("foreign_story_in_domestic_slot"), 1)

    def test_domestic_story_keeps_domestic_search_slot_when_anchor_present(self) -> None:
        items = [{
            "title": "State Bank of Pakistan announces rupee liquidity support measures",
            "summary": "SBP adjusts domestic funding conditions as banks respond to credit demand.",
            "url": "https://example.com/domestic-story",
            "published_date": "2026-08-09",
            "section": "domestic",
            "source_group": "google_topic",
            "source_weight": 8,
            "source_quality": "acceptable_media",
        }]
        retained, stats, _excluded = filter_quality_items_with_report(items, self.target_date, config=self.config)
        self.assertEqual(len(retained), 1)
        self.assertIsNone(stats.get("foreign_story_in_domestic_slot"))

    def test_mainstream_international_headline_is_retained_for_fallback(self) -> None:
        items = [{
            "title": "U.S. and Iran close to peace arrangement, Pakistan says",
            "summary": "Diplomatic talks reshape regional risk outlook.",
            "url": "https://example.com/major-headline-story",
            "published_date": "2026-08-09",
            "section": "international",
            "source_group": "cbs",
            "source_weight": 8,
            "source_quality": "tier1_media",
        }]
        retained, stats, _excluded = filter_quality_items_with_report(items, self.target_date, config=self.config)
        self.assertEqual(len(retained), 1)
        self.assertIsNone(stats.get("soft_news"))


if __name__ == "__main__":
    unittest.main()
