from __future__ import annotations

import unittest

from src.source_quality import classify_source_quality


class SourceQualityTests(unittest.TestCase):
    def test_official_source_is_allowed(self) -> None:
        quality = classify_source_quality(
            source_name="Federal Reserve",
            url="https://www.federalreserve.gov/newsevents/pressreleases.htm",
            title="Federal Reserve releases policy statement",
            summary="",
        )
        self.assertEqual(quality, "official")

    def test_broker_article_is_excluded(self) -> None:
        quality = classify_source_quality(
            source_name="Moomoo",
            url="https://www.moomoo.com/news/post/123",
            title="EUR/USD technical analysis and price target",
            summary="Broker outlook and trading signal.",
        )
        self.assertEqual(quality, "broker_or_trading_platform")

    def test_crypto_exchange_source_is_excluded(self) -> None:
        quality = classify_source_quality(
            source_name="OKX",
            url="https://www.okx.com/learn/fed-rate-hike-case",
            title="Fed rate hike case just got weaker",
            summary="Macro note published by crypto exchange research desk.",
        )
        self.assertEqual(quality, "broker_or_trading_platform")


if __name__ == "__main__":
    unittest.main()
