"""
AdvancedTimeSeriesForecaster
-----------------------------
High-level wrapper combining FinancialTimeSeriesTransformer with
IQR normalisation, a cosine-decay learning-rate schedule, and gradient
clipping for production stability.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import keras
import numpy as np
import tensorflow as tf
from ai_models.config import TransformerConfig
from ai_models.forecasting.transformer import FinancialTimeSeriesTransformer

logger = logging.getLogger(__name__)


class AdvancedTimeSeriesForecaster:
    """
    Transformer-based multi-horizon financial time-series forecaster.

    Parameters
    ----------
    config : ``TransformerConfig`` instance.
    """

    def __init__(self, config: Optional[TransformerConfig] = None) -> None:
        cfg = config or TransformerConfig()
        self.cfg = cfg
        self.model = FinancialTimeSeriesTransformer(cfg)
        self.proj = keras.layers.Dense(cfg.d_model)
        self.optimizer = keras.optimizers.Adam(
            learning_rate=keras.optimizers.schedules.CosineDecayRestarts(
                initial_learning_rate=cfg.learning_rate,
                first_decay_steps=1000,
            )
        )

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------

    @staticmethod
    def _iqr_normalise(data: np.ndarray) -> np.ndarray:
        """Robust IQR-based cross-sectional normalisation."""
        median = np.median(data, axis=1, keepdims=True)
        q75, q25 = np.percentile(data, [75, 25], axis=1, keepdims=True)
        iqr = q75 - q25
        return (data - median) / (iqr + 1e-8)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        validation_data: Optional[Tuple[np.ndarray, np.ndarray]] = None,
    ) -> Dict[str, Any]:
        """
        Train the forecaster.

        Parameters
        ----------
        x_train         : ``(N, input_seq_length, n_features)``
        y_train         : ``(N, output_seq_length)``
        epochs          : Training epochs.
        batch_size      : Mini-batch size.
        validation_data : Optional ``(x_val, y_val)`` tuple.

        Returns
        -------
        dict
            Training history with keys ``loss`` and optionally ``val_loss``.
        """
        x_norm = self._iqr_normalise(x_train)
        loss_fn = keras.losses.MeanSquaredError()
        train_ds = (
            tf.data.Dataset.from_tensor_slices((x_norm, y_train))
            .shuffle(1000)
            .batch(batch_size)
        )

        if validation_data is not None:
            x_val_norm = self._iqr_normalise(validation_data[0])
            val_ds = tf.data.Dataset.from_tensor_slices(
                (x_val_norm, validation_data[1])
            ).batch(batch_size)

        train_loss_m = keras.metrics.Mean()
        val_loss_m = keras.metrics.Mean()
        history: Dict[str, list] = {"loss": [], "val_loss": []}

        for epoch in range(epochs):
            train_loss_m.reset_state()
            for xb, yb in train_ds:
                xp = self.proj(xb)
                with tf.GradientTape() as tape:
                    pred = self.model(xp, training=True)
                    # Model may return (batch, seq, out_dim); take last time-step
                    if pred.shape.rank == 3:
                        pred = pred[:, -1, :]
                    loss = loss_fn(yb, pred)
                variables = (
                    self.model.trainable_variables + self.proj.trainable_variables
                )
                grads, _ = tf.clip_by_global_norm(tape.gradient(loss, variables), 1.0)
                self.optimizer.apply_gradients(zip(grads, variables))
                train_loss_m.update_state(loss)

            history["loss"].append(float(train_loss_m.result()))

            if validation_data is not None:
                val_loss_m.reset_state()
                for xb, yb in val_ds:
                    xp = self.proj(xb)
                    pred = self.model(xp, training=False)
                    if pred.shape.rank == 3:
                        pred = pred[:, -1, :]
                    val_loss_m.update_state(loss_fn(yb, pred))
                history["val_loss"].append(float(val_loss_m.result()))
                logger.info(
                    "Epoch %3d/%d  loss=%.5f  val_loss=%.5f",
                    epoch + 1,
                    epochs,
                    history["loss"][-1],
                    history["val_loss"][-1],
                )
            else:
                logger.info(
                    "Epoch %3d/%d  loss=%.5f", epoch + 1, epochs, history["loss"][-1]
                )

        return history

    def predict(self, x: np.ndarray) -> np.ndarray:
        """
        Generate forecasts.

        Parameters
        ----------
        x : ``(N, input_seq_length, n_features)``

        Returns
        -------
        np.ndarray ``(N, output_seq_length)``
        """
        x_norm = self._iqr_normalise(x)
        xp = self.proj(tf.cast(x_norm, tf.float32))
        return self.model(xp, training=False).numpy()

    def save(self, filepath: str) -> None:
        """
        Persist model and projection layer weights as numpy arrays.

        Saves to ``<filepath>_weights.npz`` — format-agnostic and independent
        of Keras version or TF checkpoint conventions.
        """
        import numpy as np

        weights = {f"model_{i}": w.numpy() for i, w in enumerate(self.model.weights)}
        weights.update(
            {f"proj_{i}": w.numpy() for i, w in enumerate(self.proj.weights)}
        )
        weights["_n_model"] = np.array(len(self.model.weights))
        weights["_n_proj"] = np.array(len(self.proj.weights))
        np.savez(filepath, **weights)

    def load(self, filepath: str) -> None:
        """
        Restore model and projection layer weights from ``<filepath>.npz``.

        The file must have been created by :meth:`save`.
        """
        import numpy as np

        path = filepath if filepath.endswith(".npz") else filepath + ".npz"
        data = np.load(path, allow_pickle=False)
        for i, w in enumerate(self.model.weights):
            w.assign(data[f"model_{i}"])
        for i, w in enumerate(self.proj.weights):
            w.assign(data[f"proj_{i}"])
