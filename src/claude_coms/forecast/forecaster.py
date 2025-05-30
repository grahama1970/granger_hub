"""
Main Time Series Forecaster class that orchestrates the forecasting process.

This module provides the high-level interface for forecasting that can be called
from CLI, slash commands, or MCP.

Sample input: CSV file with columns [timestamp, value] or JSON array
Expected output: Forecast object with predictions, confidence intervals, and metadata
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Union
import numpy as np
from datetime import datetime, timedelta
import json
import logging

from .ollama_forecast import OllamaForecaster
from .patches import PatchTransformer
from .data_handlers import TimeSeriesData, ForecastResult

logger = logging.getLogger(__name__)


@dataclass
class ForecastConfig:
    """Configuration for forecasting."""
    horizon: int = 24  # Number of steps to forecast
    patch_length: int = 16  # Length of each patch
    stride: int = 8  # Stride for patch creation
    confidence_levels: List[float] = None  # Default [0.5, 0.9]
    model_name: str = "auto"  # Ollama model to use
    normalization: str = "standard"  # standard, minmax, or none
    
    def __post_init__(self):
        if self.confidence_levels is None:
            self.confidence_levels = [0.5, 0.9]


class TimeSeriesForecaster:
    """Main forecaster that combines patching and Ollama for predictions."""
    
    def __init__(self, config: Optional[ForecastConfig] = None):
        self.config = config or ForecastConfig()
        self.patch_transformer = PatchTransformer(
            patch_length=self.config.patch_length,
            stride=self.config.stride
        )
        self.ollama_forecaster = OllamaForecaster(
            model_name=self.config.model_name
        )
        
    def forecast(
        self, 
        time_series: TimeSeriesData,
        horizon: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> ForecastResult:
        """
        Perform time series forecasting.
        
        Args:
            time_series: Input time series data
            horizon: Override config horizon if provided
            metadata: Additional context for forecasting
            
        Returns:
            ForecastResult with predictions and confidence intervals
        """
        horizon = horizon or self.config.horizon
        
        try:
            # Step 1: Normalize the data
            normalized_data, norm_params = self._normalize(time_series.values)
            
            # Step 2: Create patches
            patches = self.patch_transformer.create_patches(normalized_data)
            logger.info(f"Created {len(patches)} patches from {len(time_series.values)} data points")
            
            # Step 3: Get forecast from Ollama
            forecast_data = self.ollama_forecaster.forecast(
                patches=patches,
                horizon=horizon,
                context=self._create_context(time_series, metadata)
            )
            
            # Step 4: Denormalize predictions
            predictions = self._denormalize(forecast_data['predictions'], norm_params)
            
            # Step 5: Generate confidence intervals
            intervals = self._generate_intervals(
                predictions, 
                forecast_data.get('uncertainty', 0.1)
            )
            
            # Step 6: Create forecast timestamps
            last_timestamp = time_series.timestamps[-1]
            forecast_timestamps = self._generate_timestamps(
                last_timestamp, 
                horizon, 
                time_series.frequency
            )
            
            return ForecastResult(
                timestamps=forecast_timestamps,
                predictions=predictions,
                confidence_intervals=intervals,
                metadata={
                    'model': self.ollama_forecaster.get_model_info(),
                    'patch_config': {
                        'length': self.config.patch_length,
                        'stride': self.config.stride
                    },
                    'normalization': self.config.normalization,
                    'horizon': horizon,
                    'training_samples': len(time_series.values)
                }
            )
            
        except Exception as e:
            logger.error(f"Forecasting failed: {str(e)}")
            raise
    
    def _normalize(self, data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Normalize time series data."""
        if self.config.normalization == "none":
            return data, {}
            
        if self.config.normalization == "standard":
            mean = np.mean(data)
            std = np.std(data)
            normalized = (data - mean) / (std + 1e-8)
            return normalized, {"mean": mean, "std": std}
            
        elif self.config.normalization == "minmax":
            min_val = np.min(data)
            max_val = np.max(data)
            normalized = (data - min_val) / (max_val - min_val + 1e-8)
            return normalized, {"min": min_val, "max": max_val}
            
    def _denormalize(self, data: np.ndarray, params: Dict) -> np.ndarray:
        """Denormalize predictions."""
        if not params:
            return data
            
        if "mean" in params:
            return data * params["std"] + params["mean"]
        elif "min" in params:
            return data * (params["max"] - params["min"]) + params["min"]
        return data
    
    def _create_context(self, ts_data: TimeSeriesData, metadata: Optional[Dict]) -> str:
        """Create context string for Ollama."""
        context_parts = []
        
        # Add basic statistics
        context_parts.append(f"Time series with {len(ts_data.values)} observations")
        context_parts.append(f"Mean: {np.mean(ts_data.values):.2f}")
        context_parts.append(f"Std: {np.std(ts_data.values):.2f}")
        
        # Add metadata if available
        if metadata:
            for key, value in metadata.items():
                context_parts.append(f"{key}: {value}")
                
        return "; ".join(context_parts)
    
    def _generate_intervals(
        self, 
        predictions: np.ndarray, 
        uncertainty: float
    ) -> Dict[float, Tuple[np.ndarray, np.ndarray]]:
        """Generate confidence intervals for predictions."""
        intervals = {}
        
        for level in self.config.confidence_levels:
            # Simple interval generation - can be improved with better uncertainty estimation
            z_score = 1.96 if level == 0.95 else (1.645 if level == 0.9 else 0.674)
            margin = z_score * uncertainty * np.std(predictions)
            
            lower = predictions - margin
            upper = predictions + margin
            intervals[level] = (lower, upper)
            
        return intervals
    
    def _generate_timestamps(
        self, 
        last_timestamp: datetime, 
        horizon: int,
        frequency: Optional[str]
    ) -> List[datetime]:
        """Generate future timestamps based on detected frequency."""
        # Simple implementation - can be enhanced with better frequency detection
        if frequency == "hourly":
            delta = timedelta(hours=1)
        elif frequency == "daily":
            delta = timedelta(days=1)
        elif frequency == "weekly":
            delta = timedelta(weeks=1)
        else:
            # Try to infer from data
            delta = timedelta(hours=1)  # Default to hourly
            
        timestamps = []
        current = last_timestamp
        for _ in range(horizon):
            current = current + delta
            timestamps.append(current)
            
        return timestamps


# Validation function
if __name__ == "__main__":
    # Test with sample data
    import pandas as pd
    
    # Generate sample time series
    dates = pd.date_range(start='2025-01-01', periods=100, freq='H')
    values = np.sin(np.arange(100) * 0.1) + np.random.normal(0, 0.1, 100)
    
    ts_data = TimeSeriesData(
        timestamps=dates.tolist(),
        values=values,
        frequency="hourly"
    )
    
    # Create forecaster and make predictions
    forecaster = TimeSeriesForecaster()
    result = forecaster.forecast(ts_data, horizon=24)
    
    print(f"Generated {len(result.predictions)} forecast points")
    print(f"First 5 predictions: {result.predictions[:5]}")
    print(f"Confidence intervals available: {list(result.confidence_intervals.keys())}")
    print(f"Model used: {result.metadata['model']}")