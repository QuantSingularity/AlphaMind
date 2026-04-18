from typing import Optional, Tuple

import tensorflow as tf
from tensorflow.keras.layers import LSTM, Conv1D, Dense, Flatten, LeakyReLU, Reshape


class TransformerGenerator(tf.keras.layers.Layer):
    """
    Generator network for financial time series synthesis.
    Maps a latent noise vector to a synthetic price/return sequence.
    """

    def __init__(self, seq_length: int, n_features: int) -> None:
        super().__init__()
        self.seq_length = seq_length
        self.n_features = n_features
        self.dense1 = Dense(128, activation="relu")
        self.dense2 = Dense(seq_length * n_features)
        self.reshape = Reshape((seq_length, n_features))

    def call(self, inputs: tf.Tensor) -> tf.Tensor:
        x = self.dense1(inputs)
        x = self.dense2(x)
        return self.reshape(x)


class TimeSeriesDiscriminator(tf.keras.layers.Layer):
    """
    Discriminator network for financial time series.
    Uses strided 1-D convolutions to classify sequences as real or synthetic.
    """

    def __init__(self, seq_length: int) -> None:
        super().__init__()
        self.seq_length = seq_length
        self.conv1 = Conv1D(64, kernel_size=3, strides=2, padding="same")
        self.conv2 = Conv1D(128, kernel_size=3, strides=2, padding="same")
        self.flatten = Flatten()
        self.dense = Dense(1, activation="sigmoid")

    def call(self, inputs: tf.Tensor) -> tf.Tensor:
        x = self.conv1(inputs)
        x = LeakyReLU(0.2)(x)
        x = self.conv2(x)
        x = LeakyReLU(0.2)(x)
        x = self.flatten(x)
        return self.dense(x)


class RegimeClassifier(tf.keras.layers.Layer):
    """
    LSTM-based market-regime classifier.
    Identifies bull / bear / sideways / high-volatility regimes from
    a sequence of returns and macro features.
    """

    def __init__(
        self,
        n_regimes: int = 3,
        lstm_units: int = 64,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.lstm = LSTM(lstm_units, return_sequences=False, dropout=dropout)
        self.dense = Dense(n_regimes, activation="softmax")

    def call(self, inputs: tf.Tensor, training: Optional[bool] = None) -> tf.Tensor:
        x = self.lstm(inputs, training=training)
        return self.dense(x)


class FinancialTimeSeriesGAN(tf.keras.Model):
    """
    Generative Adversarial Network for synthetic financial data generation.
    Produces realistic multi-variate return sequences for data augmentation
    and stress-testing of trading strategies.
    """

    def __init__(
        self,
        seq_length: int,
        n_features: int,
        latent_dim: int = 100,
        g_lr: float = 2e-4,
        d_lr: float = 2e-4,
    ) -> None:
        super().__init__()
        self.seq_length = seq_length
        self.n_features = n_features
        self.latent_dim = latent_dim

        self.generator = TransformerGenerator(seq_length, n_features)
        self.discriminator = TimeSeriesDiscriminator(seq_length)

        self.g_optimizer = tf.keras.optimizers.Adam(g_lr, beta_1=0.5)
        self.d_optimizer = tf.keras.optimizers.Adam(d_lr, beta_1=0.5)
        self.loss_fn = tf.keras.losses.BinaryCrossentropy()

        self.g_loss_tracker = tf.keras.metrics.Mean(name="g_loss")
        self.d_loss_tracker = tf.keras.metrics.Mean(name="d_loss")

    @tf.function
    def train_step(self, real_sequences: tf.Tensor) -> Tuple[tf.Tensor, tf.Tensor]:
        """
        One training step: update discriminator then generator.

        Args:
            real_sequences: Batch of real financial sequences, shape
                (batch, seq_length, n_features).

        Returns:
            Tuple of (discriminator_loss, generator_loss).
        """
        batch_size = tf.shape(real_sequences)[0]
        noise = tf.random.normal((batch_size, self.latent_dim))

        # ---- Discriminator update ----
        with tf.GradientTape() as d_tape:
            fake_sequences = self.generator(noise, training=True)
            real_pred = self.discriminator(real_sequences, training=True)
            fake_pred = self.discriminator(fake_sequences, training=True)
            d_loss = self.loss_fn(tf.ones_like(real_pred), real_pred) + self.loss_fn(
                tf.zeros_like(fake_pred), fake_pred
            )
        d_grads = d_tape.gradient(d_loss, self.discriminator.trainable_variables)
        self.d_optimizer.apply_gradients(
            zip(d_grads, self.discriminator.trainable_variables)
        )

        # ---- Generator update ----
        with tf.GradientTape() as g_tape:
            fake_sequences = self.generator(noise, training=True)
            fake_pred = self.discriminator(fake_sequences, training=True)
            g_loss = self.loss_fn(tf.ones_like(fake_pred), fake_pred)
        g_grads = g_tape.gradient(g_loss, self.generator.trainable_variables)
        self.g_optimizer.apply_gradients(
            zip(g_grads, self.generator.trainable_variables)
        )

        self.g_loss_tracker.update_state(g_loss)
        self.d_loss_tracker.update_state(d_loss)
        return d_loss, g_loss

    def generate(self, n_samples: int) -> tf.Tensor:
        """
        Generate synthetic financial time series.

        Args:
            n_samples: Number of sequences to generate.

        Returns:
            Tensor of shape (n_samples, seq_length, n_features).
        """
        noise = tf.random.normal((n_samples, self.latent_dim))
        return self.generator(noise, training=False)


def regime_consistency_loss(regime_probs: tf.Tensor) -> tf.Tensor:
    """
    Compute a regime consistency loss that penalises diversity across the batch.

    A lower loss means the batch exhibits a *consistent* (similar) regime
    distribution across samples — i.e., the regime predictions are close to
    their batch mean.

    Args:
        regime_probs: Tensor of shape (batch_size, n_regimes) containing
            softmax probabilities output by a RegimeClassifier.

    Returns:
        Scalar loss tensor (mean squared deviation from batch mean).
    """
    mean_probs = tf.reduce_mean(regime_probs, axis=0, keepdims=True)  # (1, n_regimes)
    deviations = regime_probs - mean_probs  # (batch, n_regimes)
    return tf.reduce_mean(tf.reduce_sum(tf.square(deviations), axis=1))


class MarketGAN(tf.keras.Model):
    """
    Auxiliary-classifier GAN for synthetic financial market data generation.

    Extends :class:`FinancialTimeSeriesGAN` with an auxiliary
    :class:`RegimeClassifier` that encourages the generator to produce
    sequences consistent with identifiable market regimes.

    Attributes:
        seq_length: Length of each generated time series.
        n_features: Number of features per time step.
        latent_dim: Dimensionality of the latent noise vector.
        batch_size: Default mini-batch size used during training.
        generator: :class:`TransformerGenerator` sub-model.
        discriminator: :class:`TimeSeriesDiscriminator` sub-model.
        aux_classifier: :class:`RegimeClassifier` sub-model.
    """

    def __init__(
        self,
        seq_length: int,
        n_features: int,
        latent_dim: int = 100,
        batch_size: int = 32,
        n_regimes: int = 3,
    ) -> None:
        super().__init__()
        self.seq_length = seq_length
        self.n_features = n_features
        self.latent_dim = latent_dim
        self.batch_size = batch_size

        self.generator = TransformerGenerator(seq_length, n_features)
        self.discriminator = TimeSeriesDiscriminator(seq_length)
        self.aux_classifier = RegimeClassifier(n_regimes=n_regimes)

        self.loss_fn = tf.keras.losses.BinaryCrossentropy()

        # Optimisers are set via compile()
        self.g_optimizer: Optional[tf.keras.optimizers.Optimizer] = None
        self.d_optimizer: Optional[tf.keras.optimizers.Optimizer] = None

    # ------------------------------------------------------------------
    # Keras compile / metrics
    # ------------------------------------------------------------------

    def compile(  # type: ignore[override]
        self,
        g_optimizer: tf.keras.optimizers.Optimizer,
        d_optimizer: tf.keras.optimizers.Optimizer,
        **kwargs,
    ) -> None:
        super().compile(**kwargs)
        self.g_optimizer = g_optimizer
        self.d_optimizer = d_optimizer

    @property
    def metrics(self):
        return []

    # ------------------------------------------------------------------
    # Training step
    # ------------------------------------------------------------------

    def train_step(self, real_sequences: tf.Tensor) -> dict:
        """
        One training step: update discriminator then generator.

        Args:
            real_sequences: Batch of real financial sequences,
                shape (batch, seq_length, n_features).

        Returns:
            Dictionary with keys ``d_loss`` and ``g_loss``.
        """
        batch_size = tf.shape(real_sequences)[0]
        noise = tf.random.normal((batch_size, self.latent_dim))

        # ---- Discriminator update ----
        with tf.GradientTape() as d_tape:
            fake_sequences = self.generator(noise, training=True)
            real_pred = self.discriminator(real_sequences, training=True)
            fake_pred = self.discriminator(fake_sequences, training=True)
            d_loss = self.loss_fn(tf.ones_like(real_pred), real_pred) + self.loss_fn(
                tf.zeros_like(fake_pred), fake_pred
            )
        d_vars = self.discriminator.trainable_variables
        d_grads = d_tape.gradient(d_loss, d_vars)
        self.d_optimizer.apply_gradients(zip(d_grads, d_vars))

        # ---- Generator update (with auxiliary regime consistency) ----
        with tf.GradientTape() as g_tape:
            fake_sequences = self.generator(noise, training=True)
            fake_pred = self.discriminator(fake_sequences, training=True)
            g_loss = self.loss_fn(tf.ones_like(fake_pred), fake_pred)
            regime_probs = self.aux_classifier(fake_sequences, training=True)
            g_loss = g_loss + 0.1 * regime_consistency_loss(regime_probs)
        g_vars = (
            self.generator.trainable_variables + self.aux_classifier.trainable_variables
        )
        g_grads = g_tape.gradient(g_loss, g_vars)
        self.g_optimizer.apply_gradients(zip(g_grads, g_vars))

        return {"d_loss": d_loss, "g_loss": g_loss}

    # ------------------------------------------------------------------
    # Generation helper
    # ------------------------------------------------------------------

    def generate(self, n_samples: int) -> tf.Tensor:
        """
        Generate synthetic financial time series.

        Args:
            n_samples: Number of sequences to generate.

        Returns:
            Tensor of shape (n_samples, seq_length, n_features).
        """
        noise = tf.random.normal((n_samples, self.latent_dim))
        return self.generator(noise, training=False)
