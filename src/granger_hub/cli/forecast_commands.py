"""
CLI commands for time series forecasting functionality.

Provides --forecast flag for CLI and /forecast slash command support.
Automatically selects best model based on data characteristics.

Usage:
    claude-coms --forecast data.csv --horizon 24
    claude-coms --forecast-stream --model sklearn
    /forecast data.csv --confidence-intervals
"""

import click
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json
from typing import Optional, Union, List
import logging

from ..forecast.sklearn_wrapper import TimeSeriesRegressor, StreamingTimeSeriesRegressor
from ..forecast.data_handlers import load_time_series, save_forecast_results
from ..forecast.visualization import ForecastVisualizer

logger = logging.getLogger(__name__)


@click.group()
def forecast_cli():
    """Time series forecasting commands."""
    pass


@forecast_cli.command(name="forecast")
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--horizon', '-h', default=24, help='Number of steps to forecast')
@click.option('--model', '-m', type=click.Choice(['auto', 'patchtst', 'sklearn', 'ollama']), 
              default='auto', help='Model backend to use')
@click.option('--context-length', '-c', default=96, help='Historical context window')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.option('--confidence-intervals', '-ci', is_flag=True, help='Include confidence intervals')
@click.option('--plot', '-p', is_flag=True, help='Generate visualization')
@click.option('--graph', '-g', is_flag=True, help='Generate interactive D3.js graph')
@click.option('--serve', '-s', is_flag=True, help='Serve graph on local HTTP server')
def forecast_file(input_file, horizon, model, context_length, output, confidence_intervals, plot, graph, serve):
    """
    Forecast time series data from a CSV file.
    
    Examples:
        claude-coms forecast sales.csv --horizon 30
        claude-coms forecast metrics.csv --model patchtst --confidence-intervals
    """
    try:
        # Load data
        click.echo(f"Loading data from {input_file}...")
        data = load_time_series(input_file)
        
        # Analyze data characteristics
        data_profile = analyze_data_profile(data)
        click.echo(f"Data profile: {json.dumps(data_profile, indent=2)}")
        
        # Select model
        if model == 'auto':
            model = select_best_model(data_profile, horizon)
            click.echo(f"Auto-selected model: {model}")
        
        # Create forecaster
        forecaster = TimeSeriesRegressor(
            model_type=model,
            context_length=context_length,
            horizon=horizon
        )
        
        # Fit and predict
        click.echo(f"Training {model} model...")
        forecaster.fit(data.values)
        
        # Use last context_length points for prediction
        context = data.values[-context_length:]
        
        if confidence_intervals:
            predictions, intervals = forecaster.predict(context, return_uncertainty=True)
            click.echo(f"Generated {len(predictions)} predictions with confidence intervals")
        else:
            predictions = forecaster.predict(context)
            intervals = None
            click.echo(f"Generated {len(predictions)} predictions")
        
        # Display results
        display_results(predictions, intervals, data)
        
        # Save if requested
        if output:
            save_forecast_results(output, predictions, intervals, data)
            click.echo(f"Results saved to {output}")
        
        # Plot if requested
        if plot:
            try:
                visualize_forecast(data, predictions, intervals)
            except ImportError:
                click.echo("Plotting requires matplotlib. Install with: pip install matplotlib")
        
        # Generate interactive D3 graph if requested
        if graph:
            try:
                visualizer = ForecastVisualizer()
                
                # Extract historical values
                historical = data.values[-context_length:] if hasattr(data, 'values') else data[-context_length:]
                
                # Generate timestamps if needed
                timestamps = None
                if hasattr(data, 'timestamps'):
                    # Extend timestamps for predictions
                    from datetime import timedelta
                    last_ts = data.timestamps[-1]
                    freq = data.frequency or 'hourly'
                    delta = timedelta(hours=1) if freq == 'hourly' else timedelta(days=1)
                    
                    pred_timestamps = []
                    for i in range(1, horizon + 1):
                        pred_timestamps.append(last_ts + delta * i)
                    
                    timestamps = list(data.timestamps[-context_length:]) + pred_timestamps
                
                # Create visualization
                html_content = visualizer.create_forecast_graph(
                    historical,
                    predictions,
                    intervals,
                    timestamps=timestamps,
                    title=f"Forecast for {Path(input_file).name}"
                )
                
                # Save or serve
                if serve:
                    click.echo("Starting local server for visualization...")
                    visualizer.serve_visualization(html_content, port=8888)
                    click.echo("Press Ctrl+C to stop the server")
                    import time
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        pass
                else:
                    # Save to file
                    graph_file = output.replace('.csv', '.html') if output else 'forecast_graph.html'
                    visualizer.save_to_file(html_content, graph_file)
                    click.echo(f"Interactive graph saved to {graph_file}")
                    
            except Exception as e:
                click.echo(f"Error generating graph: {str(e)}", err=True)
                logger.exception("Graph generation failed")
                
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@forecast_cli.command(name="forecast-stream")
@click.option('--model', '-m', type=click.Choice(['auto', 'sklearn', 'ollama']), 
              default='sklearn', help='Model backend (sklearn recommended for streaming)')
@click.option('--context-length', '-c', default=50, help='Historical context window')
@click.option('--input-source', '-i', type=click.Choice(['stdin', 'socket', 'kafka']), 
              default='stdin', help='Input source for streaming data')
def forecast_stream(model, context_length, input_source):
    """
    Forecast on streaming time series data.
    
    Examples:
        echo "1.2 1.3 1.4" | claude-coms forecast-stream
        claude-coms forecast-stream --input-source socket --port 9999
    """
    try:
        # Create streaming forecaster
        click.echo(f"Starting streaming forecaster with {model} model...")
        forecaster = StreamingTimeSeriesRegressor(
            model_type=model,
            context_length=context_length,
            horizon=1  # Single-step ahead for streaming
        )
        
        # Initialize with some historical data if available
        initial_data = np.random.randn(context_length)  # Placeholder
        forecaster.fit(initial_data)
        
        click.echo("Waiting for streaming data (enter values one per line, Ctrl+C to stop)...")
        
        # Stream processing
        if input_source == 'stdin':
            for line in sys.stdin:
                try:
                    value = float(line.strip())
                    prediction = forecaster.update_and_predict(value)
                    
                    if prediction is not None:
                        metrics = forecaster.get_streaming_metrics()
                        click.echo(
                            f"Value: {value:.4f} | "
                            f"Prediction: {prediction:.4f} | "
                            f"RMSE: {metrics.get('rmse', 0):.4f}"
                        )
                except ValueError:
                    click.echo(f"Invalid input: {line.strip()}", err=True)
                    
        else:
            click.echo(f"Input source '{input_source}' not yet implemented")
            
    except KeyboardInterrupt:
        click.echo("\nStreaming stopped by user")
        metrics = forecaster.get_streaming_metrics()
        click.echo(f"Final metrics: {json.dumps(metrics, indent=2)}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


def analyze_data_profile(data) -> dict:
    """Analyze time series characteristics to guide model selection."""
    values = data.values if hasattr(data, 'values') else data
    
    profile = {
        'length': len(values),
        'is_multivariate': len(values.shape) > 1 and values.shape[1] > 1,
        'has_trend': detect_trend(values),
        'has_seasonality': detect_seasonality(values),
        'stationarity': check_stationarity(values),
        'missing_values': np.isnan(values).any(),
        'variance': np.var(values),
    }
    
    return profile


def select_best_model(profile: dict, horizon: int) -> str:
    """Select best model based on data characteristics."""
    # Decision logic based on research findings
    
    # PatchTST is best for:
    # - Multivariate data
    # - Long horizons (>48 steps)
    # - Complex patterns
    if profile['is_multivariate'] or horizon > 48:
        return 'patchtst'
    
    # Sklearn for:
    # - Simple patterns
    # - Short series (<500 points)
    # - When low latency is critical
    if profile['length'] < 500 and not profile['has_seasonality']:
        return 'sklearn'
    
    # Check if transformers are available
    try:
        import transformers
        return 'patchtst'  # Default to best accuracy
    except ImportError:
        logger.warning("Transformers not installed, falling back to ollama")
        return 'ollama'


def detect_trend(values: np.ndarray) -> bool:
    """Simple trend detection."""
    if len(values.shape) > 1:
        values = values[:, 0]  # Use first column for multivariate
    
    # Linear regression slope
    x = np.arange(len(values))
    slope = np.polyfit(x, values, 1)[0]
    
    # Significant trend if slope > 1% of value range
    return abs(slope) > 0.01 * (values.max() - values.min())


def detect_seasonality(values: np.ndarray) -> bool:
    """Simple seasonality detection using autocorrelation."""
    if len(values.shape) > 1:
        values = values[:, 0]
    
    if len(values) < 50:
        return False
    
    # Check autocorrelation at common seasonal lags
    from scipy import signal
    
    # Normalize
    values = (values - np.mean(values)) / (np.std(values) + 1e-8)
    
    # Check lags 7 (weekly), 12 (monthly), 24 (daily)
    for lag in [7, 12, 24]:
        if lag < len(values) // 2:
            correlation = np.corrcoef(values[:-lag], values[lag:])[0, 1]
            if correlation > 0.7:
                return True
    
    return False


def check_stationarity(values: np.ndarray) -> bool:
    """Check if series is stationary (simplified)."""
    if len(values.shape) > 1:
        values = values[:, 0]
    
    # Split series and compare statistics
    mid = len(values) // 2
    first_half = values[:mid]
    second_half = values[mid:]
    
    # Compare means and variances
    mean_diff = abs(np.mean(first_half) - np.mean(second_half))
    var_ratio = np.var(first_half) / (np.var(second_half) + 1e-8)
    
    # Stationary if statistics are similar
    return mean_diff < 0.1 * np.std(values) and 0.5 < var_ratio < 2.0


def display_results(predictions: np.ndarray, intervals: Optional[dict], data):
    """Display forecast results in a nice format."""
    click.echo("\n" + "="*60)
    click.echo("FORECAST RESULTS")
    click.echo("="*60)
    
    # Show first few predictions
    n_show = min(10, len(predictions))
    click.echo(f"\nFirst {n_show} predictions:")
    for i in range(n_show):
        pred_str = f"  Step {i+1}: {predictions[i]:.4f}"
        
        if intervals:
            pred_str += f" (90% CI: [{intervals['lower_90'][i]:.4f}, {intervals['upper_90'][i]:.4f}])"
        
        click.echo(pred_str)
    
    if len(predictions) > n_show:
        click.echo(f"  ... ({len(predictions) - n_show} more predictions)")
    
    # Summary statistics
    click.echo(f"\nSummary:")
    click.echo(f"  Mean prediction: {np.mean(predictions):.4f}")
    click.echo(f"  Std deviation: {np.std(predictions):.4f}")
    click.echo(f"  Min: {np.min(predictions):.4f}")
    click.echo(f"  Max: {np.max(predictions):.4f}")


def visualize_forecast(data, predictions, intervals):
    """Create forecast visualization."""
    import matplotlib.pyplot as plt
    
    # Prepare data
    historical = data.values if hasattr(data, 'values') else data
    if len(historical.shape) > 1:
        historical = historical[:, 0]  # Use first column
    
    # Create figure
    plt.figure(figsize=(12, 6))
    
    # Plot historical data
    hist_x = np.arange(len(historical))
    plt.plot(hist_x, historical, 'b-', label='Historical', alpha=0.7)
    
    # Plot predictions
    pred_x = np.arange(len(historical), len(historical) + len(predictions))
    plt.plot(pred_x, predictions, 'r--', label='Forecast', linewidth=2)
    
    # Plot confidence intervals if available
    if intervals:
        plt.fill_between(
            pred_x,
            intervals['lower_90'],
            intervals['upper_90'],
            alpha=0.3,
            color='red',
            label='90% CI'
        )
    
    # Formatting
    plt.xlabel('Time Step')
    plt.ylabel('Value')
    plt.title('Time Series Forecast')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.show()


# Integration with main CLI
def add_forecast_commands(cli_group):
    """Add forecast commands to main CLI group."""
    cli_group.add_command(forecast_cli)


# Slash command support
def handle_forecast_slash_command(args: List[str]) -> str:
    """
    Handle /forecast slash command.
    
    Args:
        args: Command arguments (e.g., ['data.csv', '--horizon', '24'])
        
    Returns:
        Result message
    """
    try:
        # Parse arguments
        if not args:
            return "Usage: /forecast <file> [--horizon N] [--model auto|patchtst|sklearn|ollama]"
        
        file_path = args[0]
        horizon = 24
        model = 'auto'
        
        # Simple argument parsing
        i = 1
        while i < len(args):
            if args[i] == '--horizon' and i + 1 < len(args):
                horizon = int(args[i + 1])
                i += 2
            elif args[i] == '--model' and i + 1 < len(args):
                model = args[i + 1]
                i += 2
            else:
                i += 1
        
        # Load data and forecast
        data = load_time_series(file_path)
        
        forecaster = TimeSeriesRegressor(
            model_type=model,
            horizon=horizon
        )
        forecaster.fit(data.values)
        
        context = data.values[-forecaster.context_length:]
        predictions = forecaster.predict(context)
        
        # Format response
        response = f"Forecast for {Path(file_path).name}:\n"
        response += f"Model: {model}\n"
        response += f"Horizon: {horizon} steps\n"
        response += f"First 5 predictions: {predictions[:5].round(4).tolist()}\n"
        response += f"Mean: {np.mean(predictions):.4f}, Std: {np.std(predictions):.4f}"
        
        return response
        
    except Exception as e:
        return f"Forecast error: {str(e)}"


if __name__ == "__main__":
    # Test the CLI
    forecast_cli()