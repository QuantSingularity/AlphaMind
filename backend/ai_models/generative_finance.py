from typing import Any, Optional

import tensorflow as tf
from tensorflow.keras.layers import LSTM, Conv1D, Dense, Flatten, LeakyReLU, Reshape


class TransformerGenerator(tf.keras.layers.Layer):
    def __init__(self, seq_length: Any, n_features: Any) -> None:
        super().__init__()
        self.seq_length = seq_length
        self.n_features = n_features
        self.dense1 = Dense(128, activation="relu")
        self.dense2 = Dense(seq_length * n_features)
        self.reshape = Reshape((seq_length, n_features))

    def call(self, inputs: Any) -> Any:
        x = self.dense1(inputs)
        x = self.dense2(x)
        return self.reshape(x)


class TimeSeriesDiscriminator(tf.keras.layers.Layer):
    def __init__(self, seq_length: Any) -> None:
        super().__init__()
        self.seq_length = seq_length
        self.conv1 = Conv1D(64, kernel_size=3, strides=2, padding="same")
        self.conv2 = Conv1D(128, kernel_size=3, strides=2, padding="same")
        self.flatten = Flatten()
        self.dense = Dense(1, activation="sigmoid")

    def call(self, inputs: Any) -> Any:
        x = self.conv1(inputs)
        x = LeakyReLU(0.2)(x)
        x = self.conv2(x)
        x = LeakyReLU(0.2)(x)
        x = self.flatten(x)
        return self.dense(x)


class RegimeClassifier(tf.keras.layers.Layer):
    def __init__(self) -> None:
        super().__init__()
        self.lstm = LSTM(64)
        self.dense = Dense(3, activation="softmax")

    def call(self, inputs: Any) -> Any:
        x = self.lstm(inputs)
        return self.dense(x)


def regime_consistency_loss(
    regime_match: Any, expected_distribution: Optional[Any] = None
) -> Any:
    if expected_distribution is None:
        expected_distribution = tf.constant([0.6, 0.3, 0.1], dtype=tf.float32)
    expected_distribution = expected_distribution / tf.reduce_sum(expected_distribution)
    regime_match = tf.clip_by_value(regime_match, 1e-08, 1.0)
    expected_broadcast = tf.broadcast_to(expected_distribution, tf.shape(regime_match))
    kl_per_sample = tf.reduce_sum(
        expected_broadcast * tf.math.log(expected_broadcast / regime_match), axis=-1
    )
    return tf.reduce_mean(kl_per_sample)


class MarketGAN(tf.keras.Model):
    """
    GAN with an Auxiliary Classifier for generating synthetic market time series.
    """

    def __init__(self, seq_length: Any, n_features: Any, batch_size: int = 32) -> None:
        super().__init__()
        self.seq_length = seq_length
        self.n_features = n_features
        self.latent_dim = 100
        self.batch_size = batch_size
        self.generator = TransformerGenerator(seq_length, n_features)
        self.discriminator = TimeSeriesDiscriminator(seq_length)
        self.aux_classifier = RegimeClassifier()
        self.loss_fn = tf.keras.losses.BinaryCrossentropy()

    def compile(self, g_optimizer: Any, d_optimizer: Any) -> Any:
        super().compile()
        self.g_optimizer = g_optimizer
        self.d_optimizer = d_optimizer

    @tf.function
    def train_step(self, real_data: Any) -> Any:
        batch_size = tf.shape(real_data)[0]
        noise = tf.random.normal(shape=[batch_size, self.latent_dim])
        fake_data = self.generator(noise)
        real_labels = tf.ones((batch_size, 1))
        fake_labels = tf.zeros((batch_size, 1))

        # Train Discriminator
        with tf.GradientTape() as d_tape:
            real_pred = self.discriminator(real_data)
            fake_pred = self.discriminator(fake_data)
            d_loss_real = self.loss_fn(real_labels, real_pred)
            d_loss_fake = self.loss_fn(fake_labels, fake_pred)
            d_loss = d_loss_real + d_loss_fake
        d_grads = d_tape.gradient(d_loss, self.discriminator.trainable_variables)
        self.d_optimizer.apply_gradients(
            zip(d_grads, self.discriminator.trainable_variables)
        )

        # Train Generator
        noise = tf.random.normal(shape=[batch_size, self.latent_dim])
        with tf.GradientTape() as g_tape:
            fake_data = self.generator(noise)
            validity = self.discriminator(fake_data)
            regime_match = self.aux_classifier(fake_data)
            aux_loss = regime_consistency_loss(regime_match)
            g_loss = self.loss_fn(real_labels, validity) + aux_loss
        g_grads = g_tape.gradient(g_loss, self.generator.trainable_variables)
        self.g_optimizer.apply_gradients(
            zip(g_grads, self.generator.trainable_variables)
        )

        return {"d_loss": d_loss, "g_loss": g_loss, "aux_loss": aux_loss}
