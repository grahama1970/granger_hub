# claude_coms/rl/episodes.py
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
import json

from .rewards import CommunicationReward
from .ollama_integration import get_ollama_client, OllamaConfig

logger = logging.getLogger(__name__)


class CommunicationEpisode:
    """Collect episodes of module communication for RL training.
    
    This class handles the collection of training episodes following
    the DeepRetrieval methodology of comparing baseline vs optimized
    approaches to compute gains. Uses Ollama for optimization.
    """
    
    def __init__(self, graph_backend, ollama_config: Optional[OllamaConfig] = None):
        self.graph_backend = graph_backend
        self.ollama_client = get_ollama_client(ollama_config)
        self.reward_fn = CommunicationReward()
        
    def collect_routing_episode(self, task: Dict) -> Dict:
        """
        Collect one episode of route optimization.
        Similar to DeepRetrieval's query optimization.
        
        Args:
            task: Dict containing:
                - source: Source module name
                - target: Target module name
                - message: Message to send
                - constraints: Optional routing constraints
        
        Returns:
            Episode data with baseline and optimized results
        """
        logger.info(f"Collecting routing episode: {task['source']} -> {task['target']}")
        
        # 1. Baseline: Direct route
        baseline_route = self._get_baseline_route(task)
        baseline_metrics = self._execute_communication(baseline_route, task.get('message'))
        baseline_reward = self.reward_fn.compute_route_reward(baseline_metrics)
        
        # 2. Optimized: Ollama-suggested route
        optimized_route = self._get_ollama_optimized_route(task)
        optimized_metrics = self._execute_communication(optimized_route, task.get('message'))
        optimized_reward = self.reward_fn.compute_route_reward(optimized_metrics)
        
        # 3. Compute gain (GBR - Gain Beyond Route)
        gain = optimized_reward - baseline_reward
        
        episode = {
            "type": "routing",
            "task": task,
            "baseline_route": baseline_route,
            "optimized_route": optimized_route,
            "baseline_metrics": baseline_metrics,
            "optimized_metrics": optimized_metrics,
            "baseline_reward": baseline_reward,
            "optimized_reward": optimized_reward,
            "gain": gain,
            "reasoning": optimized_route.get('reasoning', ''),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store episode in graph
        self._store_episode(episode)
        
        return episode
    
    def _get_baseline_route(self, task: Dict) -> Dict:
        """Get baseline route using shortest path."""
        # Direct route or shortest path from graph
        try:
            path = self.graph_backend.find_shortest_path(
                task['source'],
                task['target']
            )
        except:
            # Fallback to direct connection
            path = [task['source'], task['target']]
        
        return {
            "path": path or [task['source'], task['target']],
            "strategy": "shortest_path",
            "reasoning": "Direct shortest path from graph"
        }
    
    def _get_ollama_optimized_route(self, task: Dict) -> Dict:
        """Get optimized route using Ollama."""
        # Add graph context to task
        enriched_task = task.copy()
        enriched_task['graph_context'] = self._get_routing_context(
            task['source'], 
            task['target']
        )
        
        # Use Ollama to optimize
        result = self.ollama_client.generate_route_optimization(enriched_task)
        
        return {
            "path": result.get('route', [task['source'], task['target']]),
            "strategy": "ollama_optimized",
            "reasoning": result.get('reasoning', 'Ollama optimization'),
            "expected_metrics": {
                "latency_ms": result.get('expected_latency_ms', 100),
                "success_rate": result.get('expected_success_rate', 0.9)
            }
        }
    
    def _execute_communication(self, route: Dict, message: Any) -> Dict[str, float]:
        """Execute communication and collect metrics."""
        # In real implementation, this would actually send the message
        # For now, we simulate metrics based on route properties
        
        path = route.get('path', [])
        hops = len(path) - 1 if len(path) > 1 else 0
        
        # Simulate metrics (in real system, these would be measured)
        metrics = {
            "success_rate": 0.9 - (0.05 * hops),  # More hops = lower success
            "latency_ms": 50 + (30 * hops),  # Each hop adds latency
            "schema_compatibility": self._calculate_schema_compatibility(path),
            "hops": hops,
            "data_loss": 0.01 * hops,  # Small data loss per hop
        }
        
        # Add some randomness for realism
        import random
        for key in ['success_rate', 'latency_ms']:
            metrics[key] *= random.uniform(0.9, 1.1)
            
        return metrics
    
    def _calculate_schema_compatibility(self, path: List[str]) -> float:
        """Calculate schema compatibility along a path."""
        if len(path) <= 1:
            return 1.0
            
        # Simplified calculation - in real system would check actual schemas
        return 0.9 ** (len(path) - 1)  # Each hop reduces compatibility slightly
    
    def _store_episode(self, episode: Dict):
        """Store episode in graph for future analysis."""
        try:
            # Store in episodes collection
            self.graph_backend.db["learning_episodes"].insert(episode)
            logger.info(f"Stored episode with gain: {episode['gain']:.2f}")
        except Exception as e:
            logger.warning(f"Could not store episode in graph: {e}")
    
    def _get_routing_context(self, source: str, target: str) -> Dict:
        """Get relevant graph context for routing."""
        # Simplified context - in full implementation would query graph
        return {
            "source_info": {"name": source, "type": "module"},
            "target_info": {"name": target, "type": "module"},
            "available_paths": [
                {"path": [source, target], "latency": 150},
                {"path": [source, "Adapter", target], "latency": 120}
            ]
        }
    
    def generate_training_batch(self, episode_type: str = "routing",
                               batch_size: int = 32) -> List[Dict]:
        """
        Generate a batch of training episodes.
        
        Args:
            episode_type: Type of episodes to generate
            batch_size: Number of episodes in batch
            
        Returns:
            List of episode data
        """
        episodes = []
        
        if episode_type == "routing":
            tasks = self._generate_routing_tasks(batch_size)
            for task in tasks:
                try:
                    episode = self.collect_routing_episode(task)
                    episodes.append(episode)
                except Exception as e:
                    logger.warning(f"Failed to collect episode: {e}")
        
        return episodes
    
    def _generate_routing_tasks(self, count: int) -> List[Dict]:
        """Generate routing tasks for training."""
        # Example tasks - in real system would query actual module pairs
        module_pairs = [
            ("TemperatureSensor", "AlertModule"),
            ("PressureSensor", "DataProcessor"),
            ("HumiditySensor", "StorageModule"),
            ("DataProcessor", "AlertModule"),
            ("SensorHub", "CloudStorage")
        ]
        
        tasks = []
        import random
        
        for i in range(count):
            source, target = random.choice(module_pairs)
            task = {
                "source": source,
                "target": target,
                "message": {"type": "training", "id": f"episode_{i}"},
                "constraints": {
                    "max_latency_ms": random.choice([100, 500, 1000]),
                    "min_success_rate": random.choice([0.8, 0.9, 0.95])
                }
            }
            tasks.append(task)
            
        return tasks
