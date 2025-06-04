"""
Dynamic Interaction Discovery System

Autonomous research and test generation for multi-module interactions.
"""

from .research.research_agent import ResearchAgent
from .analysis.optimization_analyzer import OptimizationAnalyzer
from .analysis.pattern_recognizer import PatternRecognizer
from .generation.scenario_generator import ScenarioGenerator
from .learning.evolution_engine import EvolutionEngine
from .discovery_orchestrator import DiscoveryOrchestrator

__all__ = [
    "ResearchAgent",
    "OptimizationAnalyzer", 
    "PatternRecognizer",
    "ScenarioGenerator",
    "EvolutionEngine",
    "DiscoveryOrchestrator"
]