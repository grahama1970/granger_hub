"""
Module: rewards.py

External Dependencies:
- dataclasses: [Documentation URL]
- numpy: https://numpy.org/doc/

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# granger_hub/rl/rewards.py
from dataclasses import dataclass
from typing import Dict, List, Any
import numpy as np

@dataclass
class CommunicationReward:
    """Reward function for module communication optimization.
    
    Implements a DeepRetrieval-style tiered reward system that evaluates
    communication quality based on multiple metrics.
    """
    
    def compute_route_reward(self, route_metrics: Dict[str, Any]) -> float:
        """
        Compute reward for a communication route based on:
        - Latency (lower is better)
        - Success rate (higher is better)
        - Schema compatibility (higher is better)
        - Resource efficiency (lower cost is better)
        
        Args:
            route_metrics: Dict containing:
                - success_rate: float (0-1)
                - latency_ms: float
                - schema_compatibility: float (0-1)
                - hops: int (number of intermediate modules)
                - data_loss: float (0-1, lower is better)
        
        Returns:
            float: Computed reward value
        """
        # DeepRetrieval-style reward structure
        success_rate = route_metrics.get('success_rate', 0)
        latency_ms = route_metrics.get('latency_ms', float('inf'))
        schema_score = route_metrics.get('schema_compatibility', 0)
        hops = route_metrics.get('hops', 0)
        data_loss = route_metrics.get('data_loss', 0)
        
        # Tiered rewards like DeepRetrieval
        if success_rate >= 0.95:  # Excellent
            base_reward = 5.0
        elif success_rate >= 0.8:  # Good
            base_reward = 4.0
        elif success_rate >= 0.6:  # Acceptable
            base_reward = 3.0
        elif success_rate >= 0.4:  # Marginal
            base_reward = 1.0
        elif success_rate >= 0.2:  # Poor
            base_reward = 0.5
        else:  # Failed
            base_reward = -3.5
        
        # Bonus for low latency and high schema compatibility
        latency_bonus = max(0, 1.0 - (latency_ms / 1000))  # Bonus for <1s
        schema_bonus = schema_score * 2.0  # 0-2 points for schema match
        
        # Penalty for complex routes and data loss
        hop_penalty = -0.1 * max(0, hops - 1)  # Penalty for indirect routes
        data_loss_penalty = -2.0 * data_loss  # Heavy penalty for data loss
        
        return base_reward + latency_bonus + schema_bonus + hop_penalty + data_loss_penalty
    
    def compute_adaptation_reward(self, adaptation_result: Dict) -> float:
        """Reward for schema adaptation success.
        
        Args:
            adaptation_result: Dict containing:
                - success: bool
                - data_preservation_rate: float (0-1)
                - adaptation_time_ms: float
                - complexity: int (1-10)
        
        Returns:
            float: Computed reward value
        """
        if not adaptation_result.get('success', False):
            return -2.0
            
        data_preserved = adaptation_result.get('data_preservation_rate', 0)
        adaptation_time = adaptation_result.get('adaptation_time_ms', float('inf'))
        complexity = adaptation_result.get('complexity', 10)
        
        # Base reward based on data preservation
        if data_preserved >= 0.95:
            base_reward = 5.0
        elif data_preserved >= 0.8:
            base_reward = 3.0
        elif data_preserved >= 0.6:
            base_reward = 1.0
        else:
            base_reward = 0.5
            
        # Bonus for fast adaptation
        time_bonus = max(0, 1.0 - (adaptation_time / 100))  # Bonus for <100ms
        
        # Penalty for overly complex adaptations
        complexity_penalty = -0.1 * max(0, complexity - 5)
        
        return base_reward + time_bonus + complexity_penalty
    
    def compute_module_selection_reward(self, selection_result: Dict) -> float:
        """Reward for module selection decisions.
        
        Args:
            selection_result: Dict containing:
                - task_completion: bool
                - efficiency_score: float (0-1)
                - modules_used: int
                - total_latency_ms: float
        
        Returns:
            float: Computed reward value
        """
        if not selection_result.get('task_completion', False):
            return -3.0
            
        efficiency = selection_result.get('efficiency_score', 0)
        modules_used = selection_result.get('modules_used', 0)
        total_latency = selection_result.get('total_latency_ms', float('inf'))
        
        # Base reward for task completion
        base_reward = 3.0
        
        # Efficiency bonus
        efficiency_bonus = efficiency * 2.0
        
        # Bonus for using fewer modules (simpler is better)
        simplicity_bonus = max(0, 1.0 - (modules_used / 10))
        
        # Latency penalty
        latency_penalty = -min(2.0, total_latency / 5000)  # Max -2 for >5s
        
        return base_reward + efficiency_bonus + simplicity_bonus + latency_penalty
    
    def compute_detailed_metrics(self, result: Dict) -> Dict[str, float]:
        """Compute detailed metrics for analysis.
        
        Args:
            result: Communication result dictionary
        
        Returns:
            Dict with normalized metrics for logging/analysis
        """
        return {
            "success_rate": result.get('success_rate', 0),
            "latency_normalized": min(1.0, result.get('latency_ms', 0) / 1000),
            "schema_compatibility": result.get('schema_compatibility', 0),
            "efficiency_score": result.get('efficiency_score', 0),
            "data_preservation": result.get('data_preservation_rate', 1.0),
            "complexity_normalized": min(1.0, result.get('complexity', 0) / 10),
        }
