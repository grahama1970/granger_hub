"""
Scikit-learn compatible wrapper for time series forecasting models.

Provides a unified interface that works like sklearn models with fit/predict
methods, making it easy to integrate into existing ML pipelines.

Sample usage:
    forecaster = TimeSeriesRegressor(model_type="patchtst")
    forecaster.fit(X_train, y_train)
    predictions = forecaster.predict(X_test)
"""

from sklearn.base import BaseEstimator, RegressorMixin
import numpy as np
from typing import Optional, Union, Dict, List
import pandas as pd
import logging
from datetime import datetime, timedelta

from .model_backends import create_backend, ModelConfig, StreamingForecastWrapper
from .data_handlers import TimeSeriesData

logger = logging.getLogger(__name__)


class TimeSeriesRegressor(BaseEstimator, RegressorMixin):
    """
    Scikit-learn compatible time series forecaster.
    
    Can work with various backends (PatchTST, Ollama, etc.) while maintaining
    a consistent sklearn-style interface.
    
    Parameters:
    -----------
    model_type : str
        Type of model backend ('patchtst', 'ollama')
    context_length : int
        Number of historical points to use for prediction
    horizon : int
        Number of future points to predict
    model_name : str
        Specific model to load (e.g., 'ibm-granite/granite-timeseries-patchtst')
    **kwargs : dict
        Additional parameters passed to ModelConfig
    """
    
    def __init__(
        self,
        model_type: str = "patchtst",
        context_length: int = 96,
        horizon: int = 24,
        model_name: Optional[str] = None,
        **kwargs
    ):
        self.model_type = model_type
        self.context_length = context_length
        self.horizon = horizon
        self.model_name = model_name
        self.kwargs = kwargs
        
        # Will be set during fit
        self.backend_ = None
        self.is_fitted_ = False
        self.feature_names_ = None
        self.target_name_ = None
        
    def fit(self, X, y=None, **fit_params):
        """
        Fit the model on training data.
        
        Parameters:
        -----------
        X : array-like of shape (n_samples, n_features) or (n_samples,)
            Training time series data. Can be:
            - 1D array for univariate series
            - 2D array for multivariate series
            - DataFrame with time series columns
        y : array-like of shape (n_samples,), optional
            Target values (for supervised learning). If None, uses X as both
            input and target (self-supervised).
        **fit_params : dict
            Additional fitting parameters
            
        Returns:
        --------
        self : TimeSeriesRegressor
            Fitted estimator
        """
        # Handle different input types
        X_array = self._validate_input(X)
        
        # Create model configuration
        config = ModelConfig(
            model_type=self.model_type,
            model_name=self.model_name or self._get_default_model_name(),
            context_length=self.context_length,
            num_features=X_array.shape[1] if len(X_array.shape) > 1 else 1,
            **self.kwargs
        )
        
        # Create and load backend
        self.backend_ = create_backend(config)
        
        # For models that support fine-tuning
        if hasattr(self.backend_, 'fine_tune') and fit_params.get('fine_tune', False):
            # Split data for fine-tuning
            split_point = int(0.8 * len(X_array))
            train_data = X_array[:split_point]
            val_data = X_array[split_point:]
            
            try:
                self.backend_.fine_tune(train_data, val_data)
            except NotImplementedError:
                logger.warning("Fine-tuning not implemented for this backend")
        
        self.is_fitted_ = True
        return self
    
    def predict(self, X, return_uncertainty: bool = False):
        """
        Generate predictions for test data.
        
        Parameters:
        -----------
        X : array-like of shape (n_samples, n_features) or (n_samples,)
            Time series context for prediction
        return_uncertainty : bool
            Whether to return prediction intervals
            
        Returns:
        --------
        predictions : array of shape (n_samples, horizon)
            Predicted values
        uncertainty : dict, optional
            Confidence intervals if return_uncertainty=True
        """
        if not self.is_fitted_:
            raise RuntimeError("Model must be fitted before prediction")
        
        X_array = self._validate_input(X)
        
        # Handle different prediction scenarios
        if len(X_array) == self.context_length:
            # Single prediction
            result = self.backend_.predict(X_array, self.horizon)
            predictions = result["predictions"]
            
        elif len(X_array) > self.context_length:
            # Rolling window predictions
            predictions = []
            for i in range(len(X_array) - self.context_length + 1):
                context = X_array[i:i + self.context_length]
                result = self.backend_.predict(context, self.horizon)
                predictions.append(result["predictions"])
            predictions = np.array(predictions)
            
        else:
            raise ValueError(
                f"Input length ({len(X_array)}) must be >= context_length ({self.context_length})"
            )
        
        if return_uncertainty:
            # Simple uncertainty estimation (can be improved)
            std = np.std(predictions) if len(predictions.shape) > 1 else 0.1
            uncertainty = {
                "lower_50": predictions - 0.67 * std,
                "upper_50": predictions + 0.67 * std,
                "lower_90": predictions - 1.64 * std,
                "upper_90": predictions + 1.64 * std,
            }
            return predictions, uncertainty
        
        return predictions
    
    def predict_streaming(self, streaming_data):
        """
        Generate predictions on streaming data.
        
        Parameters:
        -----------
        streaming_data : iterable
            Iterator yielding new data points
            
        Yields:
        -------
        prediction : float
            Next predicted value
        """
        if not self.is_fitted_:
            raise RuntimeError("Model must be fitted before prediction")
        
        wrapper = StreamingForecastWrapper(self.backend_, self.context_length)
        
        for value in streaming_data:
            prediction = wrapper.update(value)
            if prediction is not None:
                yield prediction
    
    def score(self, X, y, sample_weight=None):
        """
        Return the coefficient of determination R^2 of the prediction.
        
        Parameters:
        -----------
        X : array-like
            Test samples
        y : array-like
            True values
        sample_weight : array-like, optional
            Sample weights
            
        Returns:
        --------
        score : float
            R^2 score
        """
        predictions = self.predict(X)
        
        # For multi-step ahead, compare only first prediction
        if len(predictions.shape) > 1:
            predictions = predictions[:, 0]
        
        # Align y with predictions
        if len(y) > len(predictions):
            y = y[:len(predictions)]
        
        # Calculate R^2
        ss_res = np.sum((y - predictions) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot)
        
        return r2
    
    def _validate_input(self, X):
        """Convert various input types to numpy array."""
        if isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)
            return X.values
        elif isinstance(X, (list, tuple)):
            return np.array(X)
        elif isinstance(X, np.ndarray):
            return X
        else:
            raise TypeError(f"Unsupported input type: {type(X)}")
    
    def _get_default_model_name(self):
        """Get default model name for each backend type."""
        defaults = {
            "patchtst": "ibm-granite/granite-timeseries-patchtst",
            "ollama": "auto",
        }
        return defaults.get(self.model_type, "auto")


class StreamingTimeSeriesRegressor(TimeSeriesRegressor):
    """
    Extension of TimeSeriesRegressor optimized for streaming applications.
    
    Maintains internal state for efficient online prediction and learning.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.streaming_wrapper_ = None
        self.metrics_history_ = []
        
    def fit(self, X, y=None, **fit_params):
        """Fit model and initialize streaming wrapper."""
        super().fit(X, y, **fit_params)
        self.streaming_wrapper_ = StreamingForecastWrapper(
            self.backend_, 
            self.context_length
        )
        return self
    
    def update_and_predict(self, new_value: float) -> Optional[float]:
        """
        Update with new value and return prediction if ready.
        
        Parameters:
        -----------
        new_value : float
            New observation
            
        Returns:
        --------
        prediction : float or None
            Next prediction if context buffer is full
        """
        if not self.is_fitted_:
            raise RuntimeError("Model must be fitted before streaming")
        
        return self.streaming_wrapper_.update(new_value)
    
    def get_streaming_metrics(self) -> Dict:
        """Get performance metrics for streaming predictions."""
        if self.streaming_wrapper_:
            return self.streaming_wrapper_.get_metrics()
        return {}


# Validation
if __name__ == "__main__":
    # Example 1: Basic usage
    print("Example 1: Basic sklearn-style usage")
    
    # Generate sample data
    t = np.linspace(0, 200, 1000)
    y = np.sin(0.1 * t) + 0.5 * np.sin(0.05 * t) + 0.1 * np.random.randn(1000)
    
    # Split data
    train_size = 800
    X_train = y[:train_size]
    X_test = y[train_size-96:train_size]  # Use last 96 points as context
    y_test = y[train_size:train_size+24]  # Next 24 points to predict
    
    # Create and fit model
    forecaster = TimeSeriesRegressor(
        model_type="ollama",  # Using Ollama as example
        context_length=96,
        horizon=24
    )
    
    try:
        forecaster.fit(X_train)
        predictions = forecaster.predict(X_test)
        
        print(f"Made {len(predictions)} predictions")
        print(f"First 5 predictions: {predictions[:5]}")
        
        # Calculate simple metric
        mae = np.mean(np.abs(predictions - y_test))
        print(f"MAE: {mae:.4f}")
        
    except Exception as e:
        print(f"Example 1 failed: {e}")
    
    # Example 2: Streaming usage
    print("\nExample 2: Streaming predictions")
    
    streaming_forecaster = StreamingTimeSeriesRegressor(
        model_type="ollama",
        context_length=50,
        horizon=1
    )
    
    try:
        # Fit on historical data
        streaming_forecaster.fit(y[:500])
        
        # Simulate streaming
        predictions = []
        for i in range(500, 600):
            pred = streaming_forecaster.update_and_predict(y[i])
            if pred is not None:
                predictions.append(pred)
                if len(predictions) % 10 == 0:
                    metrics = streaming_forecaster.get_streaming_metrics()
                    print(f"After {len(predictions)} predictions - RMSE: {metrics.get('rmse', 0):.4f}")
        
    except Exception as e:
        print(f"Example 2 failed: {e}")