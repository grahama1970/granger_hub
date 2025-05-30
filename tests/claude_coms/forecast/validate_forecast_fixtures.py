"""
Validate forecast fixtures with REAL data and REAL expected results.

Following TASK_LIST_TEMPLATE_GUIDE_V2.md requirements:
- Tests with REAL data, not fake inputs
- Verifies against concrete expected results
- No unconditional "Tests Passed" messages
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime

# Test data paths
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "forecast"


def validate_temperature_data():
    """Validate temperature data has expected properties."""
    print("\n=== Validating Temperature Data ===")
    
    df = pd.read_csv(FIXTURE_DIR / "temperature_hourly.csv")
    
    # REAL validation criteria
    expected_columns = ['timestamp', 'temperature', 'hour', 'day_of_week']
    missing_cols = set(expected_columns) - set(df.columns)
    if missing_cols:
        print(f"❌ FAILED: Missing columns: {missing_cols}")
        return False
    
    # Check data types
    if df['temperature'].dtype not in ['float64', 'int64']:
        print(f"❌ FAILED: Temperature column is not numeric: {df['temperature'].dtype}")
        return False
    
    # Check realistic temperature range (Celsius)
    min_temp = df['temperature'].min()
    max_temp = df['temperature'].max()
    if min_temp < -50 or max_temp > 60:
        print(f"❌ FAILED: Unrealistic temperatures: min={min_temp:.1f}, max={max_temp:.1f}")
        return False
    
    # Check daily pattern exists (temperature should vary by hour)
    hourly_means = df.groupby('hour')['temperature'].mean()
    temp_range = hourly_means.max() - hourly_means.min()
    if temp_range < 2.0:  # Should have at least 2°C daily variation
        print(f"❌ FAILED: No daily temperature pattern detected. Range: {temp_range:.1f}°C")
        return False
    
    # Check hottest time is afternoon (12-16)
    hottest_hour = hourly_means.idxmax()
    if not (12 <= hottest_hour <= 16):
        print(f"❌ FAILED: Hottest hour is {hottest_hour}, expected afternoon (12-16)")
        return False
    
    print(f"✅ Temperature data validated:")
    print(f"   - {len(df)} hourly records")
    print(f"   - Temperature range: {min_temp:.1f}°C to {max_temp:.1f}°C")
    print(f"   - Daily variation: {temp_range:.1f}°C")
    print(f"   - Hottest hour: {hottest_hour}:00")
    
    return True


def validate_sales_data():
    """Validate sales data has expected business patterns."""
    print("\n=== Validating Sales Data ===")
    
    df = pd.read_csv(FIXTURE_DIR / "sales_daily.csv")
    
    # Check growth trend
    first_week_avg = df['sales'][:7].mean()
    last_week_avg = df['sales'][-7:].mean()
    growth_rate = (last_week_avg - first_week_avg) / first_week_avg
    
    if growth_rate < 0:
        print(f"❌ FAILED: Sales declining instead of growing. Growth: {growth_rate:.1%}")
        return False
    
    # Check weekly pattern (weekends should be different)
    weekday_sales = df[df['is_weekend'] == False]['sales'].mean()
    weekend_sales = df[df['is_weekend'] == True]['sales'].mean()
    weekend_lift = (weekend_sales - weekday_sales) / weekday_sales
    
    if weekend_lift < 0.1:  # Expect at least 10% weekend lift
        print(f"❌ FAILED: No weekend effect detected. Lift: {weekend_lift:.1%}")
        return False
    
    # Check for December holiday spike
    december_data = df[pd.to_datetime(df['date']).dt.month == 12]
    if len(december_data) > 0:
        dec_avg = december_data['sales'].mean()
        overall_avg = df['sales'].mean()
        holiday_effect = (dec_avg - overall_avg) / overall_avg
        
        if holiday_effect < 0.2:  # Expect at least 20% holiday boost
            print(f"❌ FAILED: No holiday effect in December. Effect: {holiday_effect:.1%}")
            return False
    
    print(f"✅ Sales data validated:")
    print(f"   - {len(df)} daily records")
    print(f"   - Growth rate: {growth_rate:.1%}")
    print(f"   - Weekend lift: {weekend_lift:.1%}")
    print(f"   - Sales range: ${df['sales'].min():.0f} to ${df['sales'].max():.0f}")
    
    return True


def validate_stock_prices():
    """Validate stock price data has realistic properties."""
    print("\n=== Validating Stock Price Data ===")
    
    df = pd.read_csv(FIXTURE_DIR / "stock_prices.csv")
    
    # Calculate returns
    returns = df['returns']
    
    # Check return distribution (should be roughly normal)
    mean_return = returns.mean()
    std_return = returns.std()
    
    # Daily returns should typically be within ±5%
    extreme_returns = (returns.abs() > 0.05).sum()
    extreme_pct = extreme_returns / len(returns)
    
    if extreme_pct > 0.1:  # More than 10% extreme days is unrealistic
        print(f"❌ FAILED: Too many extreme return days: {extreme_pct:.1%}")
        return False
    
    # Check high/low/close relationship
    invalid_prices = ((df['high'] < df['close']) | 
                     (df['low'] > df['close']) |
                     (df['high'] < df['low'])).sum()
    
    if invalid_prices > 0:
        print(f"❌ FAILED: {invalid_prices} days have invalid high/low/close relationships")
        return False
    
    # Check volume is positive
    if (df['volume'] <= 0).any():
        print("❌ FAILED: Found non-positive volume values")
        return False
    
    # Calculate annualized metrics
    trading_days = 252
    annualized_return = mean_return * trading_days
    annualized_vol = std_return * np.sqrt(trading_days)
    sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0
    
    print(f"✅ Stock price data validated:")
    print(f"   - {len(df)} trading days")
    print(f"   - Annualized return: {annualized_return:.1%}")
    print(f"   - Annualized volatility: {annualized_vol:.1%}")
    print(f"   - Sharpe ratio: {sharpe_ratio:.2f}")
    print(f"   - Price range: ${df['close'].min():.2f} to ${df['close'].max():.2f}")
    
    return True


def validate_website_traffic():
    """Validate website traffic has expected patterns."""
    print("\n=== Validating Website Traffic Data ===")
    
    df = pd.read_csv(FIXTURE_DIR / "website_traffic.csv")
    
    # Check hourly pattern (should be low at night)
    night_hours = [0, 1, 2, 3, 4, 5]
    day_hours = [9, 10, 11, 12, 13, 14, 15, 16]
    
    night_traffic = df[df['hour'].isin(night_hours)]['visitors'].mean()
    day_traffic = df[df['hour'].isin(day_hours)]['visitors'].mean()
    
    if night_traffic >= day_traffic:
        print(f"❌ FAILED: Night traffic ({night_traffic:.0f}) >= day traffic ({day_traffic:.0f})")
        return False
    
    # Check weekend effect (should be lower)
    weekday_traffic = df[df['is_weekend'] == False]['visitors'].mean()
    weekend_traffic = df[df['is_weekend'] == True]['visitors'].mean()
    
    if weekend_traffic >= weekday_traffic:
        print(f"❌ FAILED: Weekend traffic not lower than weekday traffic")
        return False
    
    # Check for traffic spikes (viral events)
    threshold = df['visitors'].mean() + 3 * df['visitors'].std()
    spikes = (df['visitors'] > threshold).sum()
    
    if spikes == 0:
        print("❌ FAILED: No traffic spikes detected (unrealistic)")
        return False
    
    print(f"✅ Website traffic data validated:")
    print(f"   - {len(df)} hourly records")
    print(f"   - Day/night ratio: {day_traffic/night_traffic:.1f}x")
    print(f"   - Weekday/weekend ratio: {weekday_traffic/weekend_traffic:.1f}x")
    print(f"   - Traffic spikes: {spikes}")
    print(f"   - Visitor range: {df['visitors'].min()} to {df['visitors'].max()}")
    
    return True


def validate_energy_consumption():
    """Validate energy consumption has seasonal patterns."""
    print("\n=== Validating Energy Consumption Data ===")
    
    df = pd.read_csv(FIXTURE_DIR / "energy_consumption.csv")
    
    # Check seasonal pattern (summer/winter should be higher)
    summer_months = [6, 7, 8]
    winter_months = [12, 1, 2]
    spring_fall_months = [3, 4, 5, 9, 10, 11]
    
    summer_avg = df[df['month'].isin(summer_months)]['consumption_mwh'].mean()
    winter_avg = df[df['month'].isin(winter_months)]['consumption_mwh'].mean()
    mild_avg = df[df['month'].isin(spring_fall_months)]['consumption_mwh'].mean()
    
    # Both summer and winter should be higher than spring/fall
    if summer_avg <= mild_avg or winter_avg <= mild_avg:
        print(f"❌ FAILED: No seasonal pattern. Summer: {summer_avg:.0f}, Winter: {winter_avg:.0f}, Mild: {mild_avg:.0f}")
        return False
    
    # Check temperature correlation (U-shaped: high when too hot or cold)
    temp_bins = pd.cut(df['temperature'], bins=5)
    temp_consumption = df.groupby(temp_bins)['consumption_mwh'].mean()
    
    # Lowest consumption should be in middle bins
    if temp_consumption.idxmin() in [temp_bins.cat.categories[0], temp_bins.cat.categories[-1]]:
        print("❌ FAILED: Energy consumption not U-shaped with temperature")
        return False
    
    # Check weekend effect
    weekday_consumption = df[df['is_weekend'] == False]['consumption_mwh'].mean()
    weekend_consumption = df[df['is_weekend'] == True]['consumption_mwh'].mean()
    
    if weekend_consumption >= weekday_consumption:
        print("❌ FAILED: Weekend consumption not lower than weekday")
        return False
    
    print(f"✅ Energy consumption data validated:")
    print(f"   - {len(df)} daily records (full year)")
    print(f"   - Seasonal effect: Summer {(summer_avg/mild_avg-1)*100:.1f}%, Winter {(winter_avg/mild_avg-1)*100:.1f}%")
    print(f"   - Weekend reduction: {(1-weekend_consumption/weekday_consumption)*100:.1f}%")
    print(f"   - Consumption range: {df['consumption_mwh'].min():.0f} to {df['consumption_mwh'].max():.0f} MWh")
    
    return True


def main():
    """Run all validations."""
    print("="*60)
    print("FORECAST FIXTURE VALIDATION")
    print("="*60)
    
    results = []
    
    # Validate each dataset
    results.append(("Temperature", validate_temperature_data()))
    results.append(("Sales", validate_sales_data()))
    results.append(("Stock Prices", validate_stock_prices()))
    results.append(("Website Traffic", validate_website_traffic()))
    results.append(("Energy Consumption", validate_energy_consumption()))
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:.<20} {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed < total:
        print("\n⚠️  Some validations failed. Fix the data generation before proceeding.")
        return False
    else:
        print("\n✅ All fixtures validated successfully!")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)