from typing import Optional

import numpy as np
import tensorflow as tf


class MultiHeadAttention(tf.keras.layers.Layer):
    """
    Multi-head attention mechanism for financial time series data.
    Allows the model to jointly attend to information from different
    representation subspaces at different positions.
    """

    def __init__(self, d_model: int, num_heads: int) -> None:
        super().__init__()
        assert d_model % num_heads == 0, "d_model must be divisible by num_heads"
        self.num_heads = num_heads
        self.d_model = d_model
        self.depth: int = d_model // num_heads
        self.wq = tf.keras.layers.Dense(d_model)
        self.wk = tf.keras.layers.Dense(d_model)
        self.wv = tf.keras.layers.Dense(d_model)
        self.dense = tf.keras.layers.Dense(d_model)

    def split_heads(self, x: tf.Tensor, batch_size: int) -> tf.Tensor:
        """Split the last dimension into (num_heads, depth) and transpose."""
        x = tf.reshape(x, (batch_size, -1, self.num_heads, self.depth))
        return tf.transpose(x, perm=[0, 2, 1, 3])

    def call(
        self,
        v: tf.Tensor,
        k: tf.Tensor,
        q: tf.Tensor,
        mask: Optional[tf.Tensor] = None,
    ) -> tf.Tensor:
        batch_size = tf.shape(q)[0]
        q = self.wq(q)
        k = self.wk(k)
        v = self.wv(v)
        q = self.split_heads(q, batch_size)
        k = self.split_heads(k, batch_size)
        v = self.split_heads(v, batch_size)
        matmul_qk = tf.matmul(q, k, transpose_b=True)
        dk = tf.cast(tf.shape(k)[-1], tf.float32)
        scaled_attention_logits = matmul_qk / tf.math.sqrt(dk)
        if mask is not None:
            scaled_attention_logits += (1.0 - mask) * -1e9
        attention_weights = tf.nn.softmax(scaled_attention_logits, axis=-1)
        output = tf.matmul(attention_weights, v)
        output = tf.transpose(output, perm=[0, 2, 1, 3])
        output = tf.reshape(output, (batch_size, -1, self.d_model))
        return self.dense(output)


class TemporalAttentionBlock(tf.keras.layers.Layer):
    """
    Transformer-style encoder block combining multi-head self-attention
    with a position-wise feed-forward sublayer.
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int,
        dff: int,
        dropout_rate: float = 0.1,
    ) -> None:
        super().__init__()
        self.attention = MultiHeadAttention(d_model, num_heads)
        self.ffn = tf.keras.Sequential(
            [
                tf.keras.layers.Dense(dff, activation="relu"),
                tf.keras.layers.Dense(d_model),
            ]
        )
        self.norm1 = tf.keras.layers.LayerNormalization(epsilon=1e-6)
        self.norm2 = tf.keras.layers.LayerNormalization(epsilon=1e-6)
        self.dropout1 = tf.keras.layers.Dropout(dropout_rate)
        self.dropout2 = tf.keras.layers.Dropout(dropout_rate)

    def call(
        self,
        x: tf.Tensor,
        training: bool = False,
        mask: Optional[tf.Tensor] = None,
    ) -> tf.Tensor:
        attn_output = self.attention(x, x, x, mask)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.norm1(x + attn_output)
        ffn_output = self.ffn(out1)
        ffn_output = self.dropout2(ffn_output, training=training)
        return self.norm2(out1 + ffn_output)


def get_positional_encoding(seq_len: int, d_model: int) -> tf.Tensor:
    """
    Compute sinusoidal positional encodings.

    Args:
        seq_len: Length of the input sequence.
        d_model: Dimension of the model embeddings.

    Returns:
        Positional encoding tensor of shape (1, seq_len, d_model).
    """
    positions = np.arange(seq_len)[:, np.newaxis]
    dims = np.arange(d_model)[np.newaxis, :]
    angles = positions / np.power(10000, (2 * (dims // 2)) / np.float32(d_model))
    angles[:, 0::2] = np.sin(angles[:, 0::2])
    angles[:, 1::2] = np.cos(angles[:, 1::2])
    return tf.cast(angles[np.newaxis, :, :], dtype=tf.float32)


class FinancialTimeSeriesTransformer(tf.keras.Model):
    """
    Full Transformer encoder for financial time series forecasting.
    Combines positional encodings with stacked TemporalAttentionBlocks.
    """

    def __init__(
        self,
        num_layers: int,
        d_model: int,
        num_heads: int,
        dff: int,
        input_dim: int,
        output_dim: int,
        dropout_rate: float = 0.1,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.input_projection = tf.keras.layers.Dense(d_model)
        self.enc_layers = [
            TemporalAttentionBlock(d_model, num_heads, dff, dropout_rate)
            for _ in range(num_layers)
        ]
        self.dropout = tf.keras.layers.Dropout(dropout_rate)
        self.final_layer = tf.keras.layers.Dense(output_dim)

    def call(
        self,
        x: tf.Tensor,
        training: bool = False,
        mask: Optional[tf.Tensor] = None,
    ) -> tf.Tensor:
        seq_len = tf.shape(x)[1]
        x = self.input_projection(x)
        x += get_positional_encoding(seq_len, self.d_model)
        x = self.dropout(x, training=training)
        for layer in self.enc_layers:
            x = layer(x, training=training, mask=mask)
        # Global average pooling over time dimension
        x = tf.reduce_mean(x, axis=1)
        return self.final_layer(x)
