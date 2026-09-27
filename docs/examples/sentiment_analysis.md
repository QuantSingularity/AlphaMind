# Example: Sentiment and Alternative Data

AlphaMind exposes alternative-data sources through the API and includes a sentiment model in the research library. This example shows both.

## The alternative-data API

```bash
curl -s http://localhost:8000/api/v1/alternative-data/sources | python -m json.tool
```

Each source has a `type` (`satellite`, `sentiment`, `sec`, or `social`), a `status`, a `dataPoints` count, and a `latency`. This endpoint backs the Alternative Data screen in both clients.

## The sentiment model (research library)

A text sentiment classifier lives at `code/backend/analytics/alternative_data/sentiment_analysis.py` as `MarketSentimentAnalyzer`. It is a small embedding-based neural model (TensorFlow). Run from `code/backend` so the `analytics` package is importable, with `tensorflow` installed.

```python
from analytics.alternative_data.sentiment_analysis import MarketSentimentAnalyzer

texts = [
    "Earnings beat expectations and guidance was raised",
    "The company missed targets and cut its outlook",
    "Trading was flat with no major news",
]
labels = [1, 0, 1]  # example training labels

analyzer = MarketSentimentAnalyzer(vocab_size=500, embedding_dim=16, max_length=20)
analyzer.prepare_tokenizer(texts)
analyzer.train(texts, labels)             # see source for the full signature

scores = analyzer.get_sentiment_score([
    "Strong quarter, raising forecasts",
])
print("sentiment scores:", scores)
```

Public methods include `prepare_tokenizer`, `preprocess_text`, `train`, `predict`, `get_sentiment_score`, and `save` / `load`. Inspect the source for exact argument shapes.

## Related modules

- `analytics/alternative_data/scrapers/sec_8k_monitor.py` - an SEC 8-K monitor that computes a sentiment label per filing.
- `analytics/alternative_data/satellite_processing.py` - a satellite feature extractor.

These are library modules for experimentation. The live `/api/v1/alternative-data/sources` response is a source registry and does not run these pipelines on each request.
