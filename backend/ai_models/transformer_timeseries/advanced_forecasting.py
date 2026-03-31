import logging
from typing import Any, Optional

import keras
import numpy as np
import tensorflow as tf

from backend.ai_models.attention_mechanism import FinancialTimeSeriesTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AdvancedTimeSeriesForecaster:
    """
    Advanced time series forecasting model that combines transformer architecture
    with financial domain-specific features.
    """

    def __init__(
        self,
        input_seq_length: Any = 60,
        output_seq_length: Any = 20,
        d_model: Any = 128,
        num_heads: Any = 8,
        num_layers: Any = 4,
        dropout_rate: Any = 0.1,
    ) -> None:
        self.input_seq_length = input_seq_length
        self.output_seq_length = output_seq_length
        self.model = FinancialTimeSeriesTransformer(
            num_layers=num_layers,
            d_model=d_model,
            num_heads=num_heads,
            dff=d_model * 4,
            input_seq_length=input_seq_length,
            output_seq_length=output_seq_length,
            rate=dropout_rate,
        )
        self.feature_projection = keras.layers.Dense(d_model)
        self.optimizer = keras.optimizers.Adam(
            learning_rate=keras.optimizers.schedules.CosineDecayRestarts(
                initial_learning_rate=0.0001, first_decay_steps=1000
            )
        )

    def preprocess_data(self, data: Any) -> Any:
        """
        Preprocess financial time series data for the transformer model.

        Args:
            data: Raw financial time series data

        Returns:
            Preprocessed data ready for model input
        """
        median = np.median(data, axis=1, keepdims=True)
        q75, q25 = np.percentile(data, [75, 25], axis=1, keepdims=True)
        iqr = q75 - q25
        normalized_data = (data - median) / (iqr + 1e-08)
        try:
            self.feature_projection(normalized_data)
        except Exception:
            pass
        return normalized_data

    def train(
        self,
        X_train: Any,
        y_train: Any,
        epochs: Any = 100,
        batch_size: Any = 32,
        validation_data: Optional[Any] = None,
    ) -> Any:
        """
        Train the forecasting model.

        Args:
            X_train: Training features
            y_train: Training targets
            epochs: Number of training epochs
            batch_size: Batch size for training
            validation_data: Optional validation data tuple (X_val, y_val)

        Returns:
            Training history
        """
        X_normalized = self.preprocess_data(X_train)
        train_loss_metric = keras.metrics.Mean(name="train_loss")
        val_loss_metric = keras.metrics.Mean(name="val_loss")
        loss_fn = keras.losses.MeanSquaredError()
        train_dataset = tf.data.Dataset.from_tensor_slices((X_normalized, y_train))
        train_dataset = train_dataset.shuffle(buffer_size=1000).batch(batch_size)
        if validation_data is not None:
            X_val, y_val = validation_data
            X_val_normalized = self.preprocess_data(X_val)
            val_dataset = tf.data.Dataset.from_tensor_slices((X_val_normalized, y_val))
            val_dataset = val_dataset.batch(batch_size)
        history = {"loss": [], "val_loss": []}
        for epoch in range(epochs):
            train_loss_metric.reset_state()
            if validation_data is not None:
                val_loss_metric.reset_state()
            for x_batch, y_batch in train_dataset:
                x_projected_batch = self.feature_projection(x_batch)
                with tf.GradientTape() as tape:
                    predictions = self.model(x_projected_batch, training=True)
                    loss = loss_fn(y_batch, predictions)
                variables = (
                    self.model.trainable_variables
                    + self.feature_projection.trainable_variables
                )
                gradients = tape.gradient(loss, variables)
                gradients, _ = tf.clip_by_global_norm(gradients, clip_norm=1.0)
                self.optimizer.apply_gradients(zip(gradients, variables))
                train_loss_metric.update_state(loss)
            if validation_data is not None:
                for x_val_batch, y_val_batch in val_dataset:
                    x_val_projected_batch = self.feature_projection(x_val_batch)
                    val_predictions = self.model(x_val_projected_batch, training=False)
                    val_loss = loss_fn(y_val_batch, val_predictions)
                    val_loss_metric.update_state(val_loss)
            history["loss"].append(train_loss_metric.result().numpy())
            if validation_data is not None:
                history["val_loss"].append(val_loss_metric.result().numpy())
                logger.info(
                    f"Epoch {epoch + 1}/{epochs} - loss: {train_loss_metric.result():.4f} - val_loss: {val_loss_metric.result():.4f}"
                )
            else:
                logger.info(
                    f"Epoch {epoch + 1}/{epochs} - loss: {train_loss_metric.result():.4f}"
                )
        return history

    def predict(self, X: Any) -> Any:
        """
        Generate forecasts using the trained model.

        Args:
            X: Input features for prediction

        Returns:
            Forecasted values
        """
        X_normalized = self.preprocess_data(X)
        X_tensor = tf.convert_to_tensor(X_normalized, dtype=tf.float32)
        X_processed = self.feature_projection(X_tensor)
        predictions = self.model(X_processed, training=False)
        return predictions.numpy()

    def save(self, filepath: Any) -> Any:
        """Save the model to disk"""
        self.model.save_weights(filepath)

    def load(self, filepath: Any) -> Any:
        """Load the model from disk"""
        self.model.load_weights(filepath)
