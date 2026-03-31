import os
import sys
import unittest
from typing import Any

import numpy as np
import tensorflow as tf

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)
from ai_models.generative_finance import (
    MarketGAN,
    RegimeClassifier,
    TimeSeriesDiscriminator,
    TransformerGenerator,
    regime_consistency_loss,
)


class TestTransformerGenerator(unittest.TestCase):
    """Test suite for the TransformerGenerator class"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        self.seq_length = 20
        self.n_features = 5
        self.batch_size = 8
        self.generator = TransformerGenerator(
            seq_length=self.seq_length, n_features=self.n_features
        )
        self.latent_dim = 100
        self.inputs = tf.random.normal((self.batch_size, self.latent_dim))

    def test_initialization(self) -> Any:
        """Test that the generator initializes correctly"""
        self.assertEqual(self.generator.seq_length, self.seq_length)
        self.assertEqual(self.generator.n_features, self.n_features)

    def test_call(self) -> Any:
        """Test the call method (forward pass)"""
        output = self.generator(self.inputs)
        expected_shape = (self.batch_size, self.seq_length, self.n_features)
        self.assertEqual(output.shape, expected_shape)
        self.assertTrue(np.all(np.isfinite(output.numpy())))


class TestTimeSeriesDiscriminator(unittest.TestCase):
    """Test suite for the TimeSeriesDiscriminator class"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        self.seq_length = 20
        self.n_features = 5
        self.batch_size = 8
        self.discriminator = TimeSeriesDiscriminator(seq_length=self.seq_length)
        self.inputs = tf.random.normal(
            (self.batch_size, self.seq_length, self.n_features)
        )

    def test_initialization(self) -> Any:
        """Test that the discriminator initializes correctly"""
        self.assertEqual(self.discriminator.seq_length, self.seq_length)

    def test_call(self) -> Any:
        """Test the call method (forward pass)"""
        output = self.discriminator(self.inputs)
        expected_shape = (self.batch_size, 1)
        self.assertEqual(output.shape, expected_shape)
        self.assertTrue(np.all(output.numpy() >= 0))
        self.assertTrue(np.all(output.numpy() <= 1))


class TestRegimeClassifier(unittest.TestCase):
    """Test suite for the RegimeClassifier class"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        self.seq_length = 20
        self.n_features = 5
        self.batch_size = 8
        self.classifier = RegimeClassifier()
        self.inputs = tf.random.normal(
            (self.batch_size, self.seq_length, self.n_features)
        )

    def test_call(self) -> Any:
        """Test the call method (forward pass)"""
        output = self.classifier(self.inputs)
        expected_shape = (self.batch_size, 3)
        self.assertEqual(output.shape, expected_shape)
        row_sums = tf.reduce_sum(output, axis=1).numpy()
        for sum_val in row_sums:
            self.assertAlmostEqual(sum_val, 1.0, places=5)


class TestRegimeConsistencyLoss(unittest.TestCase):
    """Test suite for the regime_consistency_loss function"""

    def test_loss_calculation(self) -> Any:
        """Test the loss calculation"""
        regime_match = tf.constant([[0.6, 0.3, 0.1], [0.1, 0.3, 0.6]], dtype=tf.float32)
        loss = regime_consistency_loss(regime_match)
        self.assertEqual(loss.shape, ())
        self.assertTrue(np.isfinite(loss.numpy()))
        perfect_match = tf.constant(
            [[0.6, 0.3, 0.1], [0.6, 0.3, 0.1]], dtype=tf.float32
        )
        perfect_loss = regime_consistency_loss(perfect_match)
        self.assertLess(perfect_loss.numpy(), loss.numpy())


class TestMarketGAN(unittest.TestCase):
    """Test suite for the MarketGAN class"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        self.seq_length = 20
        self.n_features = 5
        self.batch_size = 8
        self.gan = MarketGAN(seq_length=self.seq_length, n_features=self.n_features)
        self.gan.batch_size = self.batch_size
        self.gan.compile(
            g_optimizer=tf.keras.optimizers.Adam(learning_rate=0.0002),
            d_optimizer=tf.keras.optimizers.Adam(learning_rate=0.0002),
        )
        self.real_data = tf.random.normal(
            (self.batch_size, self.seq_length, self.n_features)
        )

    def test_initialization(self) -> Any:
        """Test that the GAN initializes correctly"""
        self.assertEqual(self.gan.seq_length, self.seq_length)
        self.assertEqual(self.gan.n_features, self.n_features)
        self.assertEqual(self.gan.latent_dim, 100)
        self.assertEqual(self.gan.batch_size, 32)
        self.assertIsInstance(self.gan.generator, TransformerGenerator)
        self.assertIsInstance(self.gan.discriminator, TimeSeriesDiscriminator)
        self.assertIsInstance(self.gan.aux_classifier, RegimeClassifier)

    def test_train_step(self) -> Any:
        """Test a single training step"""
        losses = self.gan.train_step(self.real_data)
        self.assertIn("d_loss", losses)
        self.assertIn("g_loss", losses)
        self.assertTrue(np.isfinite(losses["d_loss"].numpy()))
        self.assertTrue(np.isfinite(losses["g_loss"].numpy()))

    def test_generator_output(self) -> Any:
        """Test generator output"""
        noise = tf.random.normal((self.batch_size, self.gan.latent_dim))
        fake_data = self.gan.generator(noise)
        expected_shape = (self.batch_size, self.seq_length, self.n_features)
        self.assertEqual(fake_data.shape, expected_shape)
        self.assertTrue(np.all(np.isfinite(fake_data.numpy())))


if __name__ == "__main__":
    unittest.main()
