"""
Test forecasting functionality with real-world data fixtures.

This test verifies that the forecasting module can handle realistic
time series data patterns including seasonality, trends, and noise.
"""

import pytest
import numpy as np
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.claude_coms.forecast import (
    load_time_series,
    TimeSeriesRegressor,
    ForecastVisualizer,
    save_forecast_results
)


class TestRealWorldForecasting:
    """Test forecasting with real-world data patterns."""
    
    @pytest.fixture
    def fixture_path(self):
        """Path to forecast fixtures."""
        return Path(__file__).parent / "fixtures" / "forecast"
    
    def test_temperature_forecasting(self, fixture_path):
        """Test forecasting hourly temperature data."""
        # Load temperature data
        data = load_time_series(fixture_path / "temperature_hourly.csv")
        
        assert len(data.values) == 720  # 30 days * 24 hours
        assert data.frequency == "hourly"
        
        # Create forecaster
        forecaster = TimeSeriesRegressor(
            model_type="ollama",  # Using Ollama for speed
            context_length=48,    # 2 days of history
            horizon=24            # Forecast 1 day ahead
        )
        
        # Fit on first 80% of data
        train_size = int(0.8 * len(data.values))
        forecaster.fit(data.values[:train_size])
        
        # Predict on test context
        test_context = data.values[train_size-48:train_size]
        predictions = forecaster.predict(test_context)
        
        # Verify predictions
        assert len(predictions) == 24
        assert np.all(np.isfinite(predictions))
        
        # Check predictions are in reasonable range (temperature)
        assert np.all(predictions > -10)  # Not below -10°C
        assert np.all(predictions < 40)   # Not above 40°C
        
        # Check predictions follow daily pattern (rough check)
        # Temperature should vary throughout the day
        assert np.std(predictions) > 1.0
    
    def test_sales_forecasting_with_trend(self, fixture_path):
        """Test forecasting daily sales with growth trend."""
        # Load sales data
        data = load_time_series(fixture_path / "sales_daily.csv", value_column="sales")
        
        assert len(data.values) == 90  # 90 days
        assert data.frequency == "daily"
        
        # Create forecaster
        forecaster = TimeSeriesRegressor(
            model_type="ollama",
            context_length=30,  # 30 days history
            horizon=7           # Forecast 1 week
        )
        
        # Fit and predict
        forecaster.fit(data.values[:60])
        predictions = forecaster.predict(data.values[30:60])
        
        # Verify predictions capture growth trend
        assert len(predictions) == 7
        assert np.mean(predictions) > np.mean(data.values[:30])  # Growth trend
        
        # Check weekly pattern exists
        # Weekend sales should be different from weekdays
        assert np.std(predictions) > 50  # Some variation expected
    
    def test_stock_price_volatility(self, fixture_path):
        """Test forecasting stock prices with realistic volatility."""
        # Load stock data
        data = load_time_series(
            fixture_path / "stock_prices.csv",
            value_column="close",
            timestamp_column="date"
        )
        
        assert len(data.values) == 252  # Trading year
        
        # Test with confidence intervals
        forecaster = TimeSeriesRegressor(
            model_type="ollama",
            context_length=20,  # 20 trading days
            horizon=5           # 5 days ahead
        )
        
        forecaster.fit(data.values[:200])
        predictions, intervals = forecaster.predict(
            data.values[180:200],
            return_uncertainty=True
        )
        
        # Check confidence intervals
        assert "lower_50" in intervals
        assert "upper_90" in intervals
        assert np.all(intervals["lower_90"] < predictions)
        assert np.all(predictions < intervals["upper_90"])
    
    def test_energy_consumption_seasonality(self, fixture_path):
        """Test forecasting energy consumption with seasonal patterns."""
        # Load energy data
        data = load_time_series(
            fixture_path / "energy_consumption.csv",
            value_column="consumption_mwh"
        )
        
        assert len(data.values) == 365  # Full year
        
        # Use longer context for seasonal patterns
        forecaster = TimeSeriesRegressor(
            model_type="ollama",
            context_length=60,   # 2 months history
            horizon=30           # 1 month forecast
        )
        
        # Fit on first 300 days
        forecaster.fit(data.values[:300])
        
        # Predict next month
        predictions = forecaster.predict(data.values[240:300])
        
        # Verify predictions are reasonable
        assert len(predictions) == 30
        assert np.mean(predictions) > 500   # Reasonable consumption
        assert np.mean(predictions) < 1500  # Not extreme
    
    def test_visualization_with_real_data(self, fixture_path, tmp_path):
        """Test creating visualizations with real data."""
        # Load website traffic data
        data = load_time_series(fixture_path / "website_traffic.csv")
        
        # Quick forecast
        forecaster = TimeSeriesRegressor(
            model_type="ollama",
            context_length=24,  # 1 day
            horizon=12          # 12 hours
        )
        
        forecaster.fit(data.values[:500])
        predictions, intervals = forecaster.predict(
            data.values[476:500],
            return_uncertainty=True
        )
        
        # Create visualization
        visualizer = ForecastVisualizer()
        html = visualizer.create_forecast_graph(
            data.values[400:500],  # Last 100 hours
            predictions,
            intervals,
            title="Website Traffic Forecast"
        )
        
        # Save to temp file
        output_file = tmp_path / "traffic_forecast.html"
        visualizer.save_to_file(html, str(output_file))
        
        # Verify file was created
        assert output_file.exists()
        assert output_file.stat().st_size > 1000  # Non-trivial HTML
        
        # Check HTML contains expected elements
        html_content = output_file.read_text()
        assert "Website Traffic Forecast" in html_content
        assert "d3.v7.min.js" in html_content
        assert "historical" in html_content
        assert "forecast" in html_content
    
    def test_streaming_with_real_patterns(self, fixture_path):
        """Test streaming forecaster with real data patterns."""
        # Load temperature data for streaming simulation
        data = load_time_series(fixture_path / "temperature_hourly.csv")
        
        # Create streaming forecaster
        from src.claude_coms.forecast import StreamingTimeSeriesRegressor
        
        forecaster = StreamingTimeSeriesRegressor(
            model_type="ollama",
            context_length=24,  # 1 day context
            horizon=1
        )
        
        # Initialize with first day
        forecaster.fit(data.values[:24])
        
        # Simulate streaming next 48 hours
        predictions = []
        for i in range(24, 72):
            pred = forecaster.update_and_predict(data.values[i])
            if pred is not None:
                predictions.append(pred)
        
        # Should have predictions after context is full
        assert len(predictions) > 0
        
        # Get streaming metrics
        metrics = forecaster.get_streaming_metrics()
        assert "rmse" in metrics
        assert metrics["n_predictions"] > 0
    
    def test_end_to_end_cli_workflow(self, fixture_path, tmp_path):
        """Test complete workflow as would be used from CLI."""
        # 1. Load data
        input_file = fixture_path / "sales_daily.csv"
        data = load_time_series(input_file, value_column="sales")
        
        # 2. Create and fit model
        forecaster = TimeSeriesRegressor(
            model_type="ollama",
            context_length=30,
            horizon=14  # 2 weeks
        )
        
        forecaster.fit(data.values)
        
        # 3. Make predictions with intervals
        context = data.values[-30:]
        predictions, intervals = forecaster.predict(
            context,
            return_uncertainty=True
        )
        
        # 4. Save results
        output_csv = tmp_path / "sales_forecast.csv"
        save_forecast_results(
            output_csv,
            predictions,
            intervals,
            data
        )
        
        # 5. Create visualization
        visualizer = ForecastVisualizer()
        html = visualizer.create_forecast_graph(
            data.values[-60:],  # Last 2 months
            predictions,
            intervals,
            timestamps=data.timestamps[-60:] + [
                data.timestamps[-1] + timedelta(days=i+1)
                for i in range(14)
            ],
            title="Sales Forecast - 2 Week Horizon"
        )
        
        output_html = tmp_path / "sales_forecast.html"
        visualizer.save_to_file(html, str(output_html))
        
        # Verify outputs
        assert output_csv.exists()
        assert output_html.exists()
        
        # Check CSV content
        import pandas as pd
        forecast_df = pd.read_csv(output_csv)
        assert len(forecast_df) == 14
        assert "prediction" in forecast_df.columns
        assert "ci_90_lower" in forecast_df.columns


# Additional validation function
if __name__ == "__main__":
    # Quick validation that fixtures exist and are valid
    from pathlib import Path
    import pandas as pd
    
    fixture_dir = Path(__file__).parent / "fixtures" / "forecast"
    
    print("Validating fixtures...")
    for csv_file in fixture_dir.glob("*.csv"):
        df = pd.read_csv(csv_file)
        print(f"\n{csv_file.name}:")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
        print(f"  First few rows:")
        print(df.head(3))
        
        # Check for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        print(f"  Numeric columns: {list(numeric_cols)}")
    
    print("\nFixtures validated successfully!")