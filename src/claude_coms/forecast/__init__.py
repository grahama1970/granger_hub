"""
Time Series Forecasting Module for Claude Module Communicator.

This module provides forecasting capabilities that can be invoked through:
- CLI: claude-coms --forecast data.csv --graph
- Slash command: /forecast data.csv
- MCP: forecast action with data input

Features:
- Multiple model backends (PatchTST, Ollama, sklearn)
- Interactive D3.js visualizations
- Streaming data support
- Confidence intervals
- Scikit-learn compatible API
"""

from .forecaster import TimeSeriesForecaster, ForecastConfig
from .data_handlers import (
    load_time_series,
    save_forecast_results,
    TimeSeriesData,
    ForecastResult
)
from .sklearn_wrapper import TimeSeriesRegressor, StreamingTimeSeriesRegressor
from .model_backends import (
    create_backend,
    ModelConfig,
    PatchTSTBackend,
    OllamaBackend,
    StreamingForecastWrapper
)
from .visualization import ForecastVisualizer

__all__ = [
    # Main classes
    "TimeSeriesForecaster",
    "TimeSeriesRegressor",
    "StreamingTimeSeriesRegressor",
    "ForecastVisualizer",
    
    # Data structures
    "TimeSeriesData",
    "ForecastResult",
    "ForecastConfig",
    "ModelConfig",
    
    # Functions
    "load_time_series",
    "save_forecast_results",
    "create_backend",
    
    # Backends
    "PatchTSTBackend",
    "OllamaBackend",
    "StreamingForecastWrapper"
]