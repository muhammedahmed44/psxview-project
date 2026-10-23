from __future__ import annotations

import unittest
from datetime import date

from src.rank import rank_items


class RankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target_date = date(2026, 8, 9)
        self.config = {
            "timezone": "Asia/Shanghai",
            "thresholds": {
                "ranking": {"watchlist_bonus": 6.0},
                "selection": {},
            },
        }

    def test_official_macro_story_ranks_above_soft_story(self) -> None:
        items = [
            {
                "title": "Central bank announces reserve ratio cut",
                "summary": "Liquidity support for banks and credit markets.",
                "raw_description": "",
                "raw_snippet": "",
                "original_source": "Federal Reserve",
                "source_group": "fed",
                "source_weight": 10,
                "section": "international",
                "published_date": "2026-08-09",
                "published_at": "2026-08-09T10:00:00+08:00",
                "quality_score": 5,
                "watchlist_hits": ["Fed"],
            },
            {
                "title": "City opens summer culture festival",
                "summary": "A lifestyle event with exhibitions and performances.",
                "raw_description": "",
                "raw_snippet": "",
                "original_source": "Local News",
                "source_group": "local",
                "source_weight": 5,
                "section": "domestic",
                "published_date": "2026-08-09",
                "published_at": "2026-08-09T10:00:00+08:00",
                "quality_score": 2,
                "watchlist_hits": [],
            },
        ]
        ranked = rank_items(items, self.config, self.target_date)
        scores = {item["title"]: item["score"] for item in ranked}
        self.assertGreater(scores["Central bank announces reserve ratio cut"], scores["City opens summer culture festival"])

    def test_inflation_story_is_bucketed_as_us_economy_policy(self) -> None:
        items = [
            {
                "title": "Inflation in focus as wage growth slows for workers",
                "summary": "U.S. CPI and wage data reinforce Federal Reserve rate-cut debate.",
                "raw_description": "",
                "raw_snippet": "",
                "original_source": "NBC News",
                "source_group": "nbc",
                "source_weight": 8,
                "section": "international",
                "published_date": "2026-08-09",
                "published_at": "2026-08-09T10:00:00+08:00",
                "quality_score": 5,
                "watchlist_hits": [],
            },
        ]
        ranked = rank_items(items, self.config, self.target_date)
        self.assertEqual(ranked[0]["category_bucket"], "us_economy_policy")

    def test_generic_international_headline_is_bucketed_as_major_headline(self) -> None:
        items = [
            {
                "title": "U.S. and Iran close to peace arrangement, Pakistan says",
                "summary": "Regional diplomacy shifts as talks continue.",
                "raw_description": "",
                "raw_snippet": "",
                "original_source": "CBS News",
                "source_group": "cbs",
                "source_weight": 8,
                "section": "international",
                "published_date": "2026-08-09",
                "published_at": "2026-08-09T10:00:00+08:00",
                "quality_score": 4,
                "watchlist_hits": [],
            },
        ]
        ranked = rank_items(items, self.config, self.target_date)
        self.assertEqual(ranked[0]["category_bucket"], "major_headline")


if __name__ == "__main__":
    unittest.main()
