from __future__ import annotations

import unittest

from src.dedupe import dedupe_items_with_report


class DedupeTests(unittest.TestCase):
    def test_same_url_is_duplicate(self) -> None:
        items = [
            {"title": "Central bank announces rate cut", "url": "https://example.com/story", "published_date": "2026-08-09", "published_at": "2026-08-09T09:00:00+08:00", "quality_score": 4, "source_weight": 8},
            {"title": "Rate cut announced by central bank", "url": "https://example.com/story?utm_source=test", "published_date": "2026-08-09", "published_at": "2026-08-09T10:00:00+08:00", "quality_score": 3, "source_weight": 7},
        ]
        kept, report = dedupe_items_with_report(items)
        self.assertEqual(len(kept), 1)
        self.assertEqual(report["stats"]["exact_url"], 1)

    def test_same_event_different_titles_is_duplicate(self) -> None:
        items = [
            {"title": "Copper miner signs supply agreement with battery maker", "url": "https://a.com/1", "published_date": "2026-08-09", "published_at": "2026-08-09T09:00:00+08:00", "quality_score": 4, "source_weight": 8},
            {"title": "Battery maker reaches copper supply deal with miner", "url": "https://b.com/2", "published_date": "2026-08-09", "published_at": "2026-08-09T09:30:00+08:00", "quality_score": 3, "source_weight": 7},
        ]
        kept, report = dedupe_items_with_report(items)
        self.assertEqual(len(kept), 1)
        self.assertGreaterEqual(report["stats"]["fuzzy_event_similarity"], 1)

    def test_same_entity_different_events_are_not_duplicate(self) -> None:
        items = [
            {"title": "Nvidia opens new data center in Singapore", "url": "https://a.com/1", "published_date": "2026-08-09", "published_at": "2026-08-09T09:00:00+08:00", "quality_score": 4, "source_weight": 8},
            {"title": "Nvidia reports quarterly earnings growth", "url": "https://b.com/2", "published_date": "2026-08-09", "published_at": "2026-08-09T10:00:00+08:00", "quality_score": 4, "source_weight": 8},
        ]
        kept, _report = dedupe_items_with_report(items)
        self.assertEqual(len(kept), 2)


if __name__ == "__main__":
    unittest.main()
