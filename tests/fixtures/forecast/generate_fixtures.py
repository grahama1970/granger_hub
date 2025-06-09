"""
Generate real-world time series data fixtures for testing.

Creates various types of time series data:
1. Hourly temperature data with daily seasonality
2. Daily sales data with weekly patterns and trend
3. Stock prices with volatility
4. Website traffic with hourly patterns
5. Energy consumption with multiple seasonalities
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))



import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)

def generate_temperature_data(days=30):
    """Generate realistic hourly temperature data."""
    hours = days * 24
    timestamps = pd.date_range(start='2024-01-01', periods=hours, freq='H')
    
    # Base temperature with daily cycle
    base_temp = 20  # 20°C average
    daily_amplitude = 5  # 5°C variation
    
    # Add seasonal trend
    seasonal_trend = np.linspace(0, 2, hours)  # Slight warming trend
    
    # Daily cycle (warmest at 2 PM, coldest at 5 AM)
    hourly_pattern = np.array([
        -4, -4.5, -5, -5, -4.5, -3.5,  # 0-5 AM (coldest)
        -2, -0.5, 1, 2.5, 3.5, 4,      # 6-11 AM (warming)
        4.5, 5, 4.5, 4, 3, 2,           # 12-5 PM (warmest)
        1, 0, -1, -2, -3, -3.5          # 6-11 PM (cooling)
    ])
    
    temperatures = []
    for i in range(hours):
        hour_of_day = i % 24
        daily_effect = hourly_pattern[hour_of_day]
        
        # Add some random noise
        noise = np.random.normal(0, 0.5)
        
        # Add weather fronts (occasional larger changes)
        if np.random.random() < 0.05:  # 5% chance of weather front
            noise += np.random.normal(0, 2)
        
        temp = base_temp + seasonal_trend[i] + daily_effect + noise
        temperatures.append(temp)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'temperature': temperatures,
        'hour': [t.hour for t in timestamps],
        'day_of_week': [t.dayofweek for t in timestamps]
    })
    
    return df


def generate_sales_data(days=90):
    """Generate realistic daily sales data with weekly patterns."""
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    
    # Base sales with growth trend
    base_sales = 1000
    growth_rate = 0.002  # 0.2% daily growth
    trend = base_sales * (1 + growth_rate) ** np.arange(days)
    
    # Weekly pattern (higher on weekends)
    weekly_pattern = np.array([0.8, 0.85, 0.9, 0.95, 1.0, 1.3, 1.2])  # Mon-Sun
    
    sales = []
    for i in range(days):
        dow = dates[i].dayofweek
        weekly_effect = weekly_pattern[dow]
        
        # Random daily variation
        daily_variation = np.random.normal(1, 0.1)
        
        # Occasional promotions (boost sales)
        if np.random.random() < 0.1:  # 10% chance
            daily_variation *= 1.5
        
        # Holiday effects
        if dates[i].month == 12 and dates[i].day > 20:  # Christmas season
            daily_variation *= 1.8
        
        daily_sales = trend[i] * weekly_effect * daily_variation
        sales.append(max(0, daily_sales))  # Ensure non-negative
    
    df = pd.DataFrame({
        'date': dates,
        'sales': sales,
        'day_of_week': [d.dayofweek for d in dates],
        'is_weekend': [d.dayofweek >= 5 for d in dates]
    })
    
    return df


def generate_stock_prices(days=252):  # Trading year
    """Generate realistic stock price data with volatility."""
    dates = pd.date_range(start='2024-01-01', periods=days, freq='B')  # Business days
    
    # Parameters
    initial_price = 100
    drift = 0.0005  # Daily expected return
    volatility = 0.02  # Daily volatility
    
    # Generate returns using geometric Brownian motion
    returns = np.random.normal(drift, volatility, days)
    
    # Add market events
    for i in range(days):
        # Earnings announcements (quarterly)
        if i % 63 == 0 and i > 0:  # Roughly quarterly
            returns[i] += np.random.normal(0, 0.03)  # Higher volatility
        
        # Random market shocks
        if np.random.random() < 0.02:  # 2% chance
            returns[i] += np.random.normal(0, 0.04)
    
    # Calculate prices
    price_multipliers = np.exp(returns)
    prices = initial_price * np.cumprod(price_multipliers)
    
    # Calculate additional metrics
    df = pd.DataFrame({
        'date': dates,
        'close': prices,
        'returns': returns,
        'high': prices * (1 + np.abs(np.random.normal(0, 0.005, days))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.005, days))),
        'volume': np.random.lognormal(15, 0.5, days).astype(int)  # Log-normal volume
    })
    
    # Ensure high >= close >= low
    df['high'] = np.maximum(df['high'], df['close'])
    df['low'] = np.minimum(df['low'], df['close'])
    
    return df


def generate_website_traffic(days=30):
    """Generate hourly website traffic data."""
    hours = days * 24
    timestamps = pd.date_range(start='2024-01-01', periods=hours, freq='H')
    
    # Base traffic
    base_traffic = 1000
    
    # Hourly pattern (peak during work hours)
    hourly_pattern = np.array([
        0.3, 0.2, 0.15, 0.1, 0.1, 0.2,    # 0-5 AM (lowest)
        0.4, 0.6, 0.9, 1.2, 1.3, 1.4,     # 6-11 AM (morning peak)
        1.2, 1.3, 1.4, 1.5, 1.4, 1.3,     # 12-5 PM (afternoon peak)
        1.1, 0.9, 0.8, 0.7, 0.6, 0.5      # 6-11 PM (evening decline)
    ])
    
    # Weekly pattern (lower on weekends)
    weekly_pattern = np.array([1.0, 1.1, 1.1, 1.0, 0.9, 0.6, 0.5])  # Mon-Sun
    
    traffic = []
    for i in range(hours):
        hour_of_day = timestamps[i].hour
        day_of_week = timestamps[i].dayofweek
        
        hourly_effect = hourly_pattern[hour_of_day]
        weekly_effect = weekly_pattern[day_of_week]
        
        # Random variation
        random_factor = np.random.lognormal(0, 0.2)
        
        # Special events (viral content, campaigns)
        if np.random.random() < 0.02:  # 2% chance
            random_factor *= np.random.uniform(2, 5)
        
        visitors = int(base_traffic * hourly_effect * weekly_effect * random_factor)
        traffic.append(max(0, visitors))
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'visitors': traffic,
        'hour': [t.hour for t in timestamps],
        'day_of_week': [t.dayofweek for t in timestamps],
        'is_weekend': [t.dayofweek >= 5 for t in timestamps]
    })
    
    return df


def generate_energy_consumption(days=365):
    """Generate daily energy consumption with multiple seasonalities."""
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    
    # Base consumption
    base_consumption = 1000  # MWh
    
    # Seasonal pattern (higher in summer and winter)
    day_of_year = np.arange(days)
    # Create U-shaped pattern: high in winter (heating) and summer (cooling)
    # Lowest in spring/fall
    # Use absolute value of sine to create two peaks per year
    seasonal_base = np.abs(np.sin(2 * np.pi * (day_of_year - 80) / 365))  # Shift so low point is in spring
    seasonal_pattern = 0.7 + 0.6 * seasonal_base  # Range from 0.7 to 1.3
    
    # Weekly pattern (lower on weekends)
    weekly_pattern = np.array([1.0, 1.0, 1.0, 1.0, 0.95, 0.8, 0.75])
    
    # Temperature effect (simplified)
    temperatures = 20 + 10 * np.sin(2 * np.pi * day_of_year / 365 - np.pi/2) + \
                   np.random.normal(0, 3, days)
    
    # Consumption increases when too hot or too cold
    temp_effect = 1 + 0.02 * np.abs(temperatures - 20)  # Optimal at 20°C
    
    consumption = []
    for i in range(days):
        dow = dates[i].dayofweek
        
        base = base_consumption * seasonal_pattern[i] * weekly_pattern[dow] * temp_effect[i]
        
        # Random daily variation
        daily_var = np.random.normal(1, 0.05)
        
        # Special events (holidays reduce consumption)
        if dates[i].month == 12 and dates[i].day in [25, 26]:  # Christmas
            daily_var *= 0.7
        elif dates[i].month == 1 and dates[i].day == 1:  # New Year
            daily_var *= 0.8
        
        daily_consumption = base * daily_var
        consumption.append(max(0, daily_consumption))
    
    df = pd.DataFrame({
        'date': dates,
        'consumption_mwh': consumption,
        'temperature': temperatures,
        'day_of_week': [d.dayofweek for d in dates],
        'month': [d.month for d in dates],
        'is_weekend': [d.dayofweek >= 5 for d in dates]
    })
    
    return df


def save_fixtures():
    """Generate and save all fixtures."""
    fixtures_dir = Path(__file__).parent
    
    # Generate all datasets
    print("Generating temperature data...")
    temp_data = generate_temperature_data(30)
    temp_data.to_csv(fixtures_dir / 'temperature_hourly.csv', index=False)
    print(f"  Saved {len(temp_data)} hourly temperature records")
    
    print("Generating sales data...")
    sales_data = generate_sales_data(90)
    sales_data.to_csv(fixtures_dir / 'sales_daily.csv', index=False)
    print(f"  Saved {len(sales_data)} daily sales records")
    
    print("Generating stock price data...")
    stock_data = generate_stock_prices(252)
    stock_data.to_csv(fixtures_dir / 'stock_prices.csv', index=False)
    print(f"  Saved {len(stock_data)} trading days of stock data")
    
    print("Generating website traffic data...")
    traffic_data = generate_website_traffic(30)
    traffic_data.to_csv(fixtures_dir / 'website_traffic.csv', index=False)
    print(f"  Saved {len(traffic_data)} hourly traffic records")
    
    print("Generating energy consumption data...")
    energy_data = generate_energy_consumption(365)
    energy_data.to_csv(fixtures_dir / 'energy_consumption.csv', index=False)
    print(f"  Saved {len(energy_data)} daily energy consumption records")
    
    # Create a metadata file
    metadata = {
        'generated_at': datetime.now().isoformat(),
        'datasets': {
            'temperature_hourly.csv': {
                'description': 'Hourly temperature data with daily seasonality',
                'frequency': 'hourly',
                'columns': list(temp_data.columns),
                'records': len(temp_data)
            },
            'sales_daily.csv': {
                'description': 'Daily sales with weekly patterns and growth trend',
                'frequency': 'daily',
                'columns': list(sales_data.columns),
                'records': len(sales_data)
            },
            'stock_prices.csv': {
                'description': 'Stock prices with realistic volatility',
                'frequency': 'business_daily',
                'columns': list(stock_data.columns),
                'records': len(stock_data)
            },
            'website_traffic.csv': {
                'description': 'Hourly website traffic with daily/weekly patterns',
                'frequency': 'hourly',
                'columns': list(traffic_data.columns),
                'records': len(traffic_data)
            },
            'energy_consumption.csv': {
                'description': 'Daily energy consumption with seasonal patterns',
                'frequency': 'daily',
                'columns': list(energy_data.columns),
                'records': len(energy_data)
            }
        }
    }
    
    with open(fixtures_dir / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\nAll fixtures generated successfully!")
    print(f"Location: {fixtures_dir}")


if __name__ == "__main__":
    save_fixtures()