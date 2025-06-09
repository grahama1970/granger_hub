"""
Data handlers for time series forecasting.
Module: data_handlers.py

Handles loading from various formats (CSV, JSON, etc.) and saving results.

Sample input formats:
- CSV: timestamp,value columns or just value column
- JSON: {"timestamps": [...], "values": [...]}
- Array: Direct numpy array or list

Expected output: TimeSeriesData object with values, timestamps, and metadata
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Union, Tuple, Any
import numpy as np
import pandas as pd
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesData:
    """Container for time series data."""
    values: np.ndarray
    timestamps: Optional[List[datetime]] = None
    frequency: Optional[str] = None  # hourly, daily, weekly, etc.
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        # Ensure values is numpy array
        if not isinstance(self.values, np.ndarray):
            self.values = np.array(self.values)
        
        # Generate timestamps if not provided
        if self.timestamps is None:
            self.timestamps = self._generate_timestamps()
        
        # Detect frequency if not provided
        if self.frequency is None and len(self.timestamps) > 1:
            self.frequency = self._detect_frequency()
    
    def _generate_timestamps(self) -> List[datetime]:
        """Generate default timestamps."""
        base = datetime.now()
        return [base - timedelta(hours=len(self.values)-i-1) for i in range(len(self.values))]
    
    def _detect_frequency(self) -> str:
        """Detect the frequency of the time series."""
        if len(self.timestamps) < 2:
            return "unknown"
        
        # Calculate average time delta
        deltas = []
        for i in range(1, min(10, len(self.timestamps))):
            delta = self.timestamps[i] - self.timestamps[i-1]
            deltas.append(delta.total_seconds())
        
        avg_seconds = np.mean(deltas)
        
        # Determine frequency
        if avg_seconds < 120:  # Less than 2 minutes
            return "minutely"
        elif avg_seconds < 7200:  # Less than 2 hours
            return "hourly"
        elif avg_seconds < 172800:  # Less than 2 days
            return "daily"
        elif avg_seconds < 1209600:  # Less than 2 weeks
            return "weekly"
        else:
            return "monthly"


@dataclass
class ForecastResult:
    """Container for forecast results."""
    predictions: np.ndarray
    timestamps: List[datetime]
    confidence_intervals: Optional[Dict[float, Tuple[np.ndarray, np.ndarray]]] = None
    metadata: Optional[Dict[str, Any]] = None


def load_time_series(
    file_path: Union[str, Path],
    value_column: Optional[str] = None,
    timestamp_column: Optional[str] = None,
    date_format: Optional[str] = None
) -> TimeSeriesData:
    """
    Load time series data from various file formats.
    
    Args:
        file_path: Path to the data file
        value_column: Name of the value column (auto-detected if None)
        timestamp_column: Name of the timestamp column (optional)
        date_format: Format string for parsing dates
        
    Returns:
        TimeSeriesData object
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Determine file type
    suffix = file_path.suffix.lower()
    
    if suffix == '.csv':
        return _load_csv(file_path, value_column, timestamp_column, date_format)
    elif suffix == '.json':
        return _load_json(file_path)
    elif suffix in ['.txt', '.dat']:
        return _load_text(file_path)
    elif suffix in ['.xlsx', '.xls']:
        return _load_excel(file_path, value_column, timestamp_column)
    else:
        # Try to load as text
        return _load_text(file_path)


def _load_csv(
    file_path: Path,
    value_column: Optional[str],
    timestamp_column: Optional[str],
    date_format: Optional[str]
) -> TimeSeriesData:
    """Load time series from CSV file."""
    try:
        # Read CSV
        df = pd.read_csv(file_path)
        
        # Find value column
        if value_column:
            if value_column not in df.columns:
                raise ValueError(f"Column '{value_column}' not found in CSV")
            values = df[value_column].values
        else:
            # Auto-detect numeric column
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) == 0:
                raise ValueError("No numeric columns found in CSV")
            
            # Use the last numeric column as values
            value_column = numeric_cols[-1]
            values = df[value_column].values
            logger.info(f"Auto-selected column '{value_column}' as values")
        
        # Find timestamp column
        timestamps = None
        if timestamp_column:
            if timestamp_column in df.columns:
                timestamps = pd.to_datetime(df[timestamp_column], format=date_format).tolist()
        else:
            # Look for common timestamp column names
            for col_name in ['timestamp', 'time', 'date', 'datetime', 'ts']:
                if col_name in df.columns:
                    try:
                        timestamps = pd.to_datetime(df[col_name], format=date_format).tolist()
                        logger.info(f"Auto-detected timestamp column: {col_name}")
                        break
                    except:
                        continue
        
        # Create metadata
        metadata = {
            'source_file': str(file_path),
            'value_column': value_column,
            'timestamp_column': timestamp_column,
            'shape': df.shape,
            'columns': list(df.columns)
        }
        
        return TimeSeriesData(
            values=values,
            timestamps=timestamps,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Failed to load CSV: {str(e)}")
        raise


def _load_json(file_path: Path) -> TimeSeriesData:
    """Load time series from JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON formats
        if isinstance(data, list):
            # Array of values
            values = np.array(data)
            timestamps = None
        elif isinstance(data, dict):
            # Dictionary format
            if 'values' in data:
                values = np.array(data['values'])
            elif 'data' in data:
                values = np.array(data['data'])
            else:
                # Try to find numeric array
                for key, val in data.items():
                    if isinstance(val, list) and len(val) > 0:
                        if isinstance(val[0], (int, float)):
                            values = np.array(val)
                            break
                else:
                    raise ValueError("No numeric data found in JSON")
            
            # Look for timestamps
            timestamps = None
            if 'timestamps' in data:
                timestamps = [datetime.fromisoformat(ts) for ts in data['timestamps']]
            elif 'time' in data:
                timestamps = [datetime.fromisoformat(ts) for ts in data['time']]
        else:
            raise ValueError(f"Unsupported JSON structure: {type(data)}")
        
        return TimeSeriesData(
            values=values,
            timestamps=timestamps,
            metadata={'source_file': str(file_path)}
        )
        
    except Exception as e:
        logger.error(f"Failed to load JSON: {str(e)}")
        raise


def _load_text(file_path: Path) -> TimeSeriesData:
    """Load time series from text file (one value per line)."""
    try:
        values = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        values.append(float(line))
                    except ValueError:
                        # Skip non-numeric lines
                        continue
        
        if not values:
            raise ValueError("No numeric values found in text file")
        
        return TimeSeriesData(
            values=np.array(values),
            metadata={'source_file': str(file_path)}
        )
        
    except Exception as e:
        logger.error(f"Failed to load text file: {str(e)}")
        raise


def _load_excel(
    file_path: Path,
    value_column: Optional[str],
    timestamp_column: Optional[str]
) -> TimeSeriesData:
    """Load time series from Excel file."""
    try:
        df = pd.read_excel(file_path)
        # Use same logic as CSV
        return _load_csv(file_path, value_column, timestamp_column, None)
    except ImportError:
        raise ImportError("Excel support requires openpyxl. Install with: pip install openpyxl")


def save_forecast_results(
    file_path: Union[str, Path],
    predictions: np.ndarray,
    confidence_intervals: Optional[Dict],
    original_data: Optional[TimeSeriesData] = None
):
    """
    Save forecast results to file.
    
    Args:
        file_path: Output file path
        predictions: Predicted values
        confidence_intervals: Optional confidence intervals
        original_data: Original time series data for context
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    
    if suffix == '.csv':
        _save_csv(file_path, predictions, confidence_intervals, original_data)
    elif suffix == '.json':
        _save_json(file_path, predictions, confidence_intervals, original_data)
    else:
        # Default to CSV
        _save_csv(file_path.with_suffix('.csv'), predictions, confidence_intervals, original_data)


def _save_csv(
    file_path: Path,
    predictions: np.ndarray,
    confidence_intervals: Optional[Dict],
    original_data: Optional[TimeSeriesData]
):
    """Save forecast results as CSV."""
    # Create DataFrame
    data = {'prediction': predictions}
    
    # Add confidence intervals if available
    if confidence_intervals:
        for level, (lower, upper) in confidence_intervals.items():
            data[f'ci_{int(level*100)}_lower'] = lower
            data[f'ci_{int(level*100)}_upper'] = upper
    
    df = pd.DataFrame(data)
    
    # Add index or timestamps
    if original_data and original_data.timestamps:
        # Generate future timestamps
        last_ts = original_data.timestamps[-1]
        freq = original_data.frequency or 'hourly'
        
        if freq == 'hourly':
            delta = timedelta(hours=1)
        elif freq == 'daily':
            delta = timedelta(days=1)
        else:
            delta = timedelta(hours=1)
        
        future_timestamps = []
        for i in range(1, len(predictions) + 1):
            future_timestamps.append(last_ts + delta * i)
        
        df['timestamp'] = future_timestamps
        df = df[['timestamp'] + [c for c in df.columns if c != 'timestamp']]
    
    df.to_csv(file_path, index=False)
    logger.info(f"Saved forecast results to {file_path}")


def _save_json(
    file_path: Path,
    predictions: np.ndarray,
    confidence_intervals: Optional[Dict],
    original_data: Optional[TimeSeriesData]
):
    """Save forecast results as JSON."""
    result = {
        'predictions': predictions.tolist(),
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'num_predictions': len(predictions)
        }
    }
    
    if confidence_intervals:
        result['confidence_intervals'] = {}
        for level, (lower, upper) in confidence_intervals.items():
            result['confidence_intervals'][str(level)] = {
                'lower': lower.tolist(),
                'upper': upper.tolist()
            }
    
    if original_data:
        result['metadata']['original_data_points'] = len(original_data.values)
        result['metadata']['frequency'] = original_data.frequency
    
    with open(file_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Saved forecast results to {file_path}")


# Validation
if __name__ == "__main__":
    # Test data loading
    import tempfile
    
    # Create test CSV
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("timestamp,value\n")
        for i in range(100):
            f.write(f"2025-01-01 {i:02d}:00:00,{np.sin(i * 0.1):.4f}\n")
        temp_path = f.name
    
    # Load data
    data = load_time_series(temp_path)
    print(f"Loaded {len(data.values)} values")
    print(f"Frequency: {data.frequency}")
    print(f"First 5 values: {data.values[:5]}")
    
    # Save test results
    predictions = np.sin(np.arange(100, 124) * 0.1)
    intervals = {
        0.9: (predictions - 0.1, predictions + 0.1)
    }
    
    save_forecast_results("test_forecast.csv", predictions, intervals, data)
    print("Saved forecast results")