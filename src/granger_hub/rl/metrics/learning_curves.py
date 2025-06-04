"""
Learning curves calculation and analysis for RL metrics.

This module queries performance metrics from ArangoDB and calculates
learning curves with moving averages and trend lines for visualization.

Third-party docs:
- ArangoDB Python Driver: https://python-arango.readthedocs.io/
- NumPy: https://numpy.org/doc/stable/
- Pandas: https://pandas.pydata.org/docs/

Sample input:
    module_name: "sparta"
    window_size: 50
    time_range: {"start": "2025-06-01T00:00:00Z", "end": "2025-06-03T23:59:59Z"}

Expected output:
    {
        "module": "sparta",
        "data_points": [...],
        "moving_average": [...],
        "trend_line": {...},
        "confidence_intervals": {...}
    }
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from arango import ArangoClient
from arango.database import Database

logger = logging.getLogger(__name__)


class LearningCurvesCalculator:
    """Calculate learning curves from RL metrics stored in ArangoDB."""
    
    def __init__(self, db: Optional[Database] = None):
        """Initialize with ArangoDB connection."""
        self.db = db
        if not self.db:
            # Connect to ArangoDB
            client = ArangoClient(hosts='http://localhost:8529')
            self.db = client.db('granger_test', username='root', password='openSesame')
    
    def query_module_metrics(
        self, 
        module_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query performance metrics for a specific module.
        
        Args:
            module_name: Name of the module to query
            start_time: Start of time range (default: 7 days ago)
            end_time: End of time range (default: now)
            limit: Maximum number of records to return
            
        Returns:
            List of metric records sorted by timestamp
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)
        if not end_time:
            end_time = datetime.utcnow()
            
        query = '''
        FOR metric IN rl_metrics
            FILTER metric.module_name == @module_name
            FILTER metric.timestamp >= @start_time
            FILTER metric.timestamp <= @end_time
            SORT metric.timestamp ASC
            LIMIT @limit
            RETURN {
                timestamp: metric.timestamp,
                episode: metric.episode,
                reward: metric.reward,
                success_rate: metric.success_rate,
                exploration_rate: metric.exploration_rate,
                learning_rate: metric.learning_rate,
                loss: metric.loss,
                duration_ms: metric.duration_ms
            }
        '''
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={
                'module_name': module_name,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'limit': limit
            }
        )
        
        return list(cursor)
    
    def calculate_moving_average(
        self, 
        data: List[float], 
        window_size: int = 50
    ) -> List[float]:
        """Calculate moving average of the data.
        
        Args:
            data: List of values
            window_size: Window size for moving average
            
        Returns:
            List of moving average values
        """
        if len(data) < window_size:
            window_size = max(1, len(data) // 4)
            
        df = pd.Series(data)
        ma = df.rolling(window=window_size, min_periods=1).mean()
        return ma.tolist()
    
    def calculate_trend_line(
        self, 
        x_data: List[float], 
        y_data: List[float]
    ) -> Dict[str, float]:
        """Calculate linear trend line using least squares.
        
        Args:
            x_data: X-axis values (e.g., episode numbers)
            y_data: Y-axis values (e.g., rewards)
            
        Returns:
            Dictionary with slope, intercept, r_squared
        """
        if len(x_data) < 2 or len(y_data) < 2:
            return {'slope': 0, 'intercept': 0, 'r_squared': 0}
            
        x = np.array(x_data)
        y = np.array(y_data)
        
        # Calculate trend line
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = coeffs
        
        # Calculate R-squared
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            'slope': float(slope),
            'intercept': float(intercept),
            'r_squared': float(r_squared)
        }
    
    def calculate_confidence_intervals(
        self, 
        data: List[float], 
        confidence: float = 0.95
    ) -> Dict[str, List[float]]:
        """Calculate confidence intervals for the data.
        
        Args:
            data: List of values
            confidence: Confidence level (default: 95%)
            
        Returns:
            Dictionary with upper and lower bounds
        """
        if len(data) < 2:
            return {'upper': data, 'lower': data}
            
        df = pd.Series(data)
        mean = df.mean()
        std = df.std()
        
        # Calculate z-score for confidence level
        z_score = 1.96 if confidence == 0.95 else 2.58  # 95% or 99%
        margin = z_score * (std / np.sqrt(len(data)))
        
        upper = [mean + margin] * len(data)
        lower = [mean - margin] * len(data)
        
        return {
            'upper': upper,
            'lower': lower,
            'mean': float(mean),
            'std': float(std)
        }
    
    def get_learning_curves(
        self,
        module_name: str,
        window_size: int = 50,
        time_range: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Get complete learning curve data for a module.
        
        Args:
            module_name: Name of the module
            window_size: Window size for moving average
            time_range: Optional time range with 'start' and 'end' ISO strings
            
        Returns:
            Complete learning curve data including raw data, moving averages,
            trend lines, and confidence intervals
        """
        # Parse time range
        start_time = None
        end_time = None
        if time_range:
            if 'start' in time_range:
                start_time = datetime.fromisoformat(time_range['start'].replace('Z', '+00:00'))
            if 'end' in time_range:
                end_time = datetime.fromisoformat(time_range['end'].replace('Z', '+00:00'))
        
        # Query metrics
        metrics = self.query_module_metrics(module_name, start_time, end_time)
        
        if not metrics:
            return {
                'module': module_name,
                'data_points': [],
                'moving_average': [],
                'trend_line': {'slope': 0, 'intercept': 0, 'r_squared': 0},
                'confidence_intervals': {'upper': [], 'lower': [], 'mean': 0, 'std': 0},
                'summary': {
                    'total_episodes': 0,
                    'avg_reward': 0,
                    'max_reward': 0,
                    'min_reward': 0,
                    'improvement_rate': 0
                }
            }
        
        # Extract data series
        episodes = [m['episode'] for m in metrics]
        rewards = [m['reward'] for m in metrics]
        success_rates = [m['success_rate'] for m in metrics]
        
        # Calculate moving averages
        ma_rewards = self.calculate_moving_average(rewards, window_size)
        ma_success = self.calculate_moving_average(success_rates, window_size)
        
        # Calculate trend lines
        reward_trend = self.calculate_trend_line(episodes, rewards)
        success_trend = self.calculate_trend_line(episodes, success_rates)
        
        # Calculate confidence intervals
        reward_ci = self.calculate_confidence_intervals(rewards)
        
        # Calculate summary statistics
        summary = {
            'total_episodes': len(episodes),
            'avg_reward': float(np.mean(rewards)),
            'max_reward': float(np.max(rewards)),
            'min_reward': float(np.min(rewards)),
            'improvement_rate': reward_trend['slope'],
            'final_success_rate': success_rates[-1] if success_rates else 0
        }
        
        return {
            'module': module_name,
            'data_points': metrics,
            'moving_average': {
                'rewards': ma_rewards,
                'success_rates': ma_success
            },
            'trend_line': {
                'rewards': reward_trend,
                'success_rates': success_trend
            },
            'confidence_intervals': reward_ci,
            'summary': summary
        }
    
    def get_module_comparison(
        self,
        module_names: List[str],
        metric: str = 'reward',
        window_size: int = 50
    ) -> Dict[str, Any]:
        """Compare learning curves across multiple modules.
        
        Args:
            module_names: List of module names to compare
            metric: Metric to compare ('reward' or 'success_rate')
            window_size: Window size for moving average
            
        Returns:
            Comparison data for all modules
        """
        comparison = {
            'modules': {},
            'best_performer': None,
            'metric': metric
        }
        
        best_score = float('-inf')
        best_module = None
        
        for module in module_names:
            curves = self.get_learning_curves(module, window_size)
            
            # Extract relevant metric
            if metric == 'reward':
                final_score = curves['summary']['avg_reward']
            else:
                final_score = curves['summary']['final_success_rate']
            
            comparison['modules'][module] = {
                'final_score': final_score,
                'improvement_rate': curves['trend_line']['rewards']['slope'],
                'total_episodes': curves['summary']['total_episodes']
            }
            
            if final_score > best_score:
                best_score = final_score
                best_module = module
        
        comparison['best_performer'] = best_module
        return comparison


if __name__ == "__main__":
    # Test with real data
    calculator = LearningCurvesCalculator()
    
    # Test 1: Get learning curves for a single module
    print("\n=== Test 1: Single Module Learning Curves ===")
    curves = calculator.get_learning_curves(
        "sparta",
        window_size=50,
        time_range={
            "start": "2025-06-01T00:00:00Z",
            "end": "2025-06-03T23:59:59Z"
        }
    )
    print(f"Module: {curves['module']}")
    print(f"Total episodes: {curves['summary']['total_episodes']}")
    print(f"Average reward: {curves['summary']['avg_reward']:.2f}")
    print(f"Improvement rate: {curves['summary']['improvement_rate']:.4f}")
    
    # Test 2: Compare multiple modules
    print("\n=== Test 2: Module Comparison ===")
    comparison = calculator.get_module_comparison(
        ["sparta", "marker", "pdf_extractor"],
        metric="reward"
    )
    print(f"Best performer: {comparison['best_performer']}")
    for module, stats in comparison['modules'].items():
        print(f"  {module}: score={stats['final_score']:.2f}, rate={stats['improvement_rate']:.4f}")
    
    # Test 3: Module drill-down
    print("\n=== Test 3: Module Drill-down ===")
    metrics = calculator.query_module_metrics("sparta", limit=10)
    print(f"Retrieved {len(metrics)} recent metrics")
    if metrics:
        latest = metrics[-1]
        print(f"Latest metric: episode={latest['episode']}, reward={latest['reward']:.2f}")

    def calculate_learning_curves(self, module_name: str, window_size: int = 50, metric: str = "reward") -> Dict[str, Any]:
        """Calculate learning curves for a module (alias for get_learning_curves)."""
        return self.get_learning_curves(module_name, window_size, metric)
    
    def get_module_drill_down(self, module_name: str, episode_range: Tuple[int, int] = (0, 1000), include_raw_data: bool = True) -> Dict[str, Any]:
        """Get detailed drill-down data for a specific module."""
        query = """
        FOR metric IN rl_metrics
            FILTER metric.module_name == @module_name
            FILTER metric.episode >= @start_episode
            FILTER metric.episode <= @end_episode
            SORT metric.episode ASC
            RETURN metric
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "module_name": module_name,
                "start_episode": episode_range[0],
                "end_episode": episode_range[1]
            }
        )
        
        metrics = list(cursor)
        
        if metrics:
            rewards = [m["reward"] for m in metrics]
            success_rates = [m.get("success_rate", 0) for m in metrics]
            
            statistics = {
                "episode_range": {
                    "start": metrics[0]["episode"],
                    "end": metrics[-1]["episode"]
                },
                "reward_stats": {
                    "mean": np.mean(rewards),
                    "max": np.max(rewards),
                    "min": np.min(rewards),
                    "std": np.std(rewards)
                },
                "success_rate_stats": {
                    "mean": np.mean(success_rates),
                    "max": np.max(success_rates),
                    "min": np.min(success_rates),
                    "std": np.std(success_rates)
                },
                "total_records": len(metrics)
            }
        else:
            statistics = {
                "episode_range": {"start": 0, "end": 0},
                "reward_stats": {"mean": 0, "max": 0, "min": 0, "std": 0},
                "success_rate_stats": {"mean": 0, "max": 0, "min": 0, "std": 0},
                "total_records": 0
            }
        
        return {
            "module": module_name,
            "metrics": metrics if include_raw_data else [],
            "statistics": statistics
        }
