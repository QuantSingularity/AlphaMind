"""
Unit tests for MarketSentimentAnalyzer (analytics/alternative_data/sentiment_analysis.py).

Strategy: test without a GPU, using minimal vocab/sequence sizes to keep
tests fast. Heavy training is explicitly skipped or mocked.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

try:
    import tensorflow as tf

    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TF_AVAILABLE, reason="TensorFlow not installed")


@pytest.fixture(scope="module")
def analyzer():
    from analytics.alternative_data.sentiment_analysis import MarketSentimentAnalyzer

    return MarketSentimentAnalyzer(vocab_size=500, embedding_dim=16, max_length=20)


@pytest.fixture(scope="module")
def sample_texts():
    return [
        "Strong earnings beat expectations revenue soared",
        "Company misses earnings guidance cut outlook",
        "Market neutral analyst maintains hold rating",
        "Record profits driven by AI growth",
        "Layoffs announced amid restructuring losses",
    ]


@pytest.fixture(scope="module")
def sample_labels():
    return [2, 0, 1, 2, 0]  # 0=negative, 1=neutral, 2=positive


class TestModelArchitecture:
    def test_model_not_none(self, analyzer):
        assert analyzer.model is not None

    def test_model_is_keras(self, analyzer):
        assert isinstance(analyzer.model, tf.keras.Model)

    def test_output_units(self, analyzer):
        """Final Dense layer should have 3 units (neg/neutral/pos)."""
        last_layer = analyzer.model.layers[-1]
        assert last_layer.units == 3

    def test_output_activation_softmax(self, analyzer):
        config = analyzer.model.layers[-1].get_config()
        assert "softmax" in config.get("activation", "")


class TestTokenizerPreparation:
    def test_tokenizer_none_before_prepare(self):
        from analytics.alternative_data.sentiment_analysis import (
            MarketSentimentAnalyzer,
        )

        a = MarketSentimentAnalyzer(vocab_size=100, max_length=10)
        assert a.tokenizer is None

    def test_tokenizer_set_after_prepare(self, analyzer, sample_texts):
        analyzer.prepare_tokenizer(sample_texts)
        assert analyzer.tokenizer is not None

    def test_preprocess_raises_without_tokenizer(self):
        from analytics.alternative_data.sentiment_analysis import (
            MarketSentimentAnalyzer,
        )

        a = MarketSentimentAnalyzer(vocab_size=100, max_length=10)
        with pytest.raises(ValueError, match="Tokenizer not initialized"):
            a.preprocess_text(["hello world"])


class TestPreprocessing:
    def test_output_shape(self, analyzer, sample_texts):
        analyzer.prepare_tokenizer(sample_texts)
        out = analyzer.preprocess_text(sample_texts)
        assert out.shape == (len(sample_texts), analyzer.max_length)

    def test_output_dtype_integer(self, analyzer, sample_texts):
        analyzer.prepare_tokenizer(sample_texts)
        out = analyzer.preprocess_text(sample_texts)
        assert np.issubdtype(out.dtype, np.integer)

    def test_padding_to_max_length(self, analyzer):
        analyzer.prepare_tokenizer(["a"])
        out = analyzer.preprocess_text(["a"])
        assert out.shape[1] == analyzer.max_length

    def test_oov_token_handles_unknown_words(self, analyzer, sample_texts):
        analyzer.prepare_tokenizer(sample_texts)
        # Completely unseen vocabulary
        out = analyzer.preprocess_text(["zxqwerty frobnicator"])
        assert out.shape == (1, analyzer.max_length)


class TestPrediction:
    def test_predict_output_shape(self, analyzer, sample_texts):
        analyzer.prepare_tokenizer(sample_texts)
        sequences = analyzer.preprocess_text(sample_texts[:2])
        preds = analyzer.model.predict(sequences, verbose=0)
        assert preds.shape == (2, 3)

    def test_predict_probabilities_sum_to_one(self, analyzer, sample_texts):
        analyzer.prepare_tokenizer(sample_texts)
        seqs = analyzer.preprocess_text(sample_texts)
        preds = analyzer.model.predict(seqs, verbose=0)
        np.testing.assert_allclose(preds.sum(axis=1), 1.0, atol=1e-5)

    def test_predict_values_in_zero_one(self, analyzer, sample_texts):
        analyzer.prepare_tokenizer(sample_texts)
        seqs = analyzer.preprocess_text(sample_texts)
        preds = analyzer.model.predict(seqs, verbose=0)
        assert np.all(preds >= 0) and np.all(preds <= 1)
