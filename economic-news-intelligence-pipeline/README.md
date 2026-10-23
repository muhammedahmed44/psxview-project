# Pakistan economic news intelligenc

This patch replaces the five YAML configuration files for the Pakistan-market adaptation of [`economic-news-intelligence-pipeline`](https://github.com/cynikjinchen/economic-news-intelligence-pipeline).

## Updated Files
- `config.yaml`: switches runtime timezone to `Asia/Karachi` and retains the existing API configuration pattern.
- `config/sources.yaml`: Pakistan official institutions, local business publishers, Pakistan-focused Google News RSS queries, and a limited set of global sources that affect Pakistan.
- `config/keywords.yaml`: Pakistan economic taxonomy, ranking terms, source-quality anchors, English terms, and a small Urdu starter set.
- `config/source_quality.yaml`: source tiers and existing financial-promotion denylist.
- `config/thresholds.yaml`: Pakistan source-group selection limits and greater domestic macro/market coverage.


