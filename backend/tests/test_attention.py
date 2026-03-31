import os
import sys
import unittest
from typing import Any

import numpy as np
import tensorflow as tf

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)
from ai_models.attention_mechanism import (
    FinancialTimeSeriesTransformer,
    MultiHeadAttention,
    TemporalAttentionBlock,
    get_positional_encoding,
)


class TestMultiHeadAttention(unittest.TestCase):
    """Test suite for the MultiHeadAttention class"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        self.d_model = 64
        self.num_heads = 4
        self.batch_size = 8
        self.seq_length = 10
        self.attention = MultiHeadAttention(
            d_model=self.d_model, num_heads=self.num_heads
        )
        self.query = tf.random.normal((self.batch_size, self.seq_length, self.d_model))
        self.key = tf.random.normal((self.batch_size, self.seq_length, self.d_model))
        self.value = tf.random.normal((self.batch_size, self.seq_length, self.d_model))

    def test_initialization(self) -> Any:
        """Test that the MultiHeadAttention initializes correctly"""
        self.assertEqual(self.attention.d_model, self.d_model)
        self.assertEqual(self.attention.num_heads, self.num_heads)
        self.assertEqual(self.attention.depth, self.d_model // self.num_heads)

    def test_split_heads(self) -> Any:
        """Test the split_heads method"""
        x = tf.random.normal((self.batch_size, self.seq_length, self.d_model))
        split = self.attention.split_heads(x, self.batch_size)
        expected_shape = (
            self.batch_size,
            self.num_heads,
            self.seq_length,
            self.d_model // self.num_heads,
        )
        self.assertEqual(split.shape, expected_shape)

    def test_call(self) -> Any:
        """Test the call method (forward pass)"""
        output = self.attention(self.value, self.key, self.query)
        expected_shape = (self.batch_size, self.seq_length, self.d_model)
        self.assertEqual(output.shape, expected_shape)

    def test_mask(self) -> Any:
        """Test attention with mask"""
        mask = np.ones((self.batch_size, 1, self.seq_length, self.seq_length))
        mask_half = self.seq_length // 2
        mask[:, :, :mask_half, mask_half:] = 0
        mask = tf.constant(mask, dtype=tf.float32)
        output_with_mask = self.attention(self.value, self.key, self.query, mask=mask)
        output_without_mask = self.attention(self.value, self.key, self.query)
        self.assertFalse(
            np.allclose(
                output_with_mask.numpy(), output_without_mask.numpy(), atol=0.001
            )
        )
        expected_shape = (self.batch_size, self.seq_length, self.d_model)
        self.assertEqual(output_with_mask.shape, expected_shape)


class TestTemporalAttentionBlock(unittest.TestCase):
    """Test suite for the TemporalAttentionBlock class"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        self.d_model = 64
        self.num_heads = 4
        self.dff = 256
        self.batch_size = 8
        self.seq_length = 10
        self.block = TemporalAttentionBlock(
            d_model=self.d_model, num_heads=self.num_heads, dff=self.dff
        )
        self.x = tf.random.normal((self.batch_size, self.seq_length, self.d_model))

    def test_initialization(self) -> Any:
        """Test that the TemporalAttentionBlock initializes correctly"""
        self.assertIsInstance(self.block.mha, MultiHeadAttention)
        self.assertEqual(self.block.mha.d_model, self.d_model)
        self.assertEqual(self.block.mha.num_heads, self.num_heads)

    def test_call(self) -> Any:
        """Test the call method (forward pass)"""
        output = self.block(self.x)
        expected_shape = (self.batch_size, self.seq_length, self.d_model)
        self.assertEqual(output.shape, expected_shape)

    def test_training_mode(self) -> Any:
        """Test the block in training and inference modes"""
        output_training = self.block(self.x, training=True)
        output_inference = self.block(self.x, training=False)
        self.assertFalse(
            np.allclose(output_training.numpy(), output_inference.numpy(), atol=0.01)
        )

    def test_mask(self) -> Any:
        """Test the block with a mask"""
        mask = tf.zeros((self.batch_size, 1, 1, self.seq_length))
        output_with_mask = self.block(self.x, mask=mask)
        expected_shape = (self.batch_size, self.seq_length, self.d_model)
        self.assertEqual(output_with_mask.shape, expected_shape)


class TestPositionalEncoding(unittest.TestCase):
    """Test suite for the positional encoding function"""

    def test_shape(self) -> Any:
        """Test the shape of the positional encoding"""
        seq_length = 20
        d_model = 64
        pos_encoding = get_positional_encoding(seq_length, d_model)
        expected_shape = (1, seq_length, d_model)
        self.assertEqual(pos_encoding.shape, expected_shape)

    def test_values(self) -> Any:
        """Test specific values in the positional encoding"""
        seq_length = 10
        d_model = 8
        pos_encoding = get_positional_encoding(seq_length, d_model).numpy()[0]
        for pos in range(seq_length):
            for i in range(0, d_model, 2):
                expected_value = np.sin(pos / 10000 ** (i / d_model))
                self.assertAlmostEqual(pos_encoding[pos, i], expected_value, places=5)
                if i + 1 < d_model:
                    expected_value = np.cos(pos / 10000 ** (i / d_model))
                    self.assertAlmostEqual(
                        pos_encoding[pos, i + 1], expected_value, places=5
                    )


class TestFinancialTimeSeriesTransformer(unittest.TestCase):
    """Test suite for the FinancialTimeSeriesTransformer class"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        self.num_layers = 2
        self.d_model = 64
        self.num_heads = 4
        self.dff = 256
        self.input_seq_length = 20
        self.output_seq_length = 5
        self.batch_size = 8
        self.transformer = FinancialTimeSeriesTransformer(
            num_layers=self.num_layers,
            d_model=self.d_model,
            num_heads=self.num_heads,
            dff=self.dff,
            input_seq_length=self.input_seq_length,
            output_seq_length=self.output_seq_length,
        )
        self.x = tf.random.normal(
            (self.batch_size, self.input_seq_length, self.d_model)
        )

    def test_initialization(self) -> Any:
        """Test that the transformer initializes correctly"""
        self.assertEqual(self.transformer.d_model, self.d_model)
        self.assertEqual(self.transformer.num_layers, self.num_layers)
        self.assertEqual(self.transformer.input_seq_length, self.input_seq_length)
        self.assertEqual(self.transformer.output_seq_length, self.output_seq_length)
        self.assertEqual(len(self.transformer.enc_layers), self.num_layers)

    def test_call(self) -> Any:
        """Test the call method (forward pass)"""
        output = self.transformer(self.x)
        expected_shape = (
            self.batch_size,
            self.input_seq_length,
            self.output_seq_length,
        )
        self.assertEqual(output.shape, expected_shape)

    def test_training_mode(self) -> Any:
        """Test the transformer in training and inference modes"""
        output_training = self.transformer(self.x, training=True)
        output_inference = self.transformer(self.x, training=False)
        self.assertFalse(
            np.allclose(output_training.numpy(), output_inference.numpy(), atol=0.01)
        )

    def test_mask(self) -> Any:
        """Test the transformer with a mask"""
        mask = tf.zeros((self.batch_size, 1, 1, self.input_seq_length))
        output_with_mask = self.transformer(self.x, mask=mask)
        expected_shape = (
            self.batch_size,
            self.input_seq_length,
            self.output_seq_length,
        )
        self.assertEqual(output_with_mask.shape, expected_shape)

    def test_end_to_end(self) -> Any:
        """Test an end-to-end forward pass with random data"""
        input_data = tf.random.normal(
            (self.batch_size, self.input_seq_length, self.d_model)
        )
        output = self.transformer(input_data)
        expected_shape = (
            self.batch_size,
            self.input_seq_length,
            self.output_seq_length,
        )
        self.assertEqual(output.shape, expected_shape)
        self.assertTrue(np.all(np.isfinite(output.numpy())))


if __name__ == "__main__":
    unittest.main()
