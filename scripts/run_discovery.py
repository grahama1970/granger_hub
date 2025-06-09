#!/usr/bin/env python3
"""
Run the Dynamic Interaction Discovery System

This script demonstrates the discovery system in action.
"""

import asyncio
import sys
from pathlib import Path
import argparse
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from granger_hub.discovery import DiscoveryOrchestrator
from loguru import logger


async def run_discovery(
    categories: list = None,
    force_refresh: bool = False,
    max_scenarios: int = 5
):
    """Run a discovery cycle"""
    logger.info(" Starting Dynamic Interaction Discovery System")
    
    # Create orchestrator
    orchestrator = DiscoveryOrchestrator()
    
    # Configure for this run
    if max_scenarios:
        orchestrator.config["max_scenarios_per_run"] = max_scenarios
    
    # Run discovery cycle
    logger.info(" Beginning discovery cycle...")
    run = await orchestrator.run_discovery_cycle(
        categories=categories,
        force_refresh=force_refresh
    )
    
    # Print results
    print("\n" + "="*60)
    print(" Discovery Results")
    print("="*60)
    print(f"Run ID: {run.run_id}")
    print(f"Duration: {(run.end_time - run.start_time).total_seconds():.1f}s")
    print(f"\n Findings:")
    print(f"  - Research items found: {run.findings_count}")
    print(f"  - Patterns discovered: {run.patterns_discovered}")
    print(f"  - Scenarios generated: {run.scenarios_generated}")
    print(f"  - Scenarios saved: {len(run.scenarios_saved)}")
    
    if run.errors:
        print(f"\n⚠️  Errors encountered: {len(run.errors)}")
        for error in run.errors[:3]:
            print(f"  - {error}")
    
    print(f"\n Metrics:")
    for key, value in run.metrics.items():
        if isinstance(value, float):
            print(f"  - {key}: {value:.2f}")
        else:
            print(f"  - {key}: {value}")
    
    # Show saved scenarios
    if run.scenarios_saved:
        print(f"\n Generated Scenarios:")
        for path in run.scenarios_saved[:5]:
            print(f"  - {Path(path).name}")
    
    # Get learning insights
    print(f"\n Learning Insights:")
    stats = orchestrator.get_statistics()
    print(f"  - Total runs: {stats['total_runs']}")
    print(f"  - Success rate: {stats['success_rate']:.1%}")
    print(f"  - Total scenarios generated: {stats['total_scenarios_generated']}")
    
    print("\n Discovery cycle complete!")
    
    return run


async def test_components():
    """Test individual components"""
    print(" Testing Discovery System Components\n")
    
    # Test Research Agent
    print("1️⃣ Testing Research Agent...")
    from granger_hub.discovery.research import ResearchAgent
    agent = ResearchAgent()
    findings = await agent.conduct_research(categories=["optimization"], force_refresh=False)
    print(f"    Found {len(findings)} research items")
    if findings:
        print(f"    Top finding: {findings[0].title[:50]}...")
    
    # Test Pattern Recognizer
    print("\n2️⃣ Testing Pattern Recognizer...")
    from granger_hub.discovery.analysis import PatternRecognizer
    recognizer = PatternRecognizer()
    patterns = await recognizer.recognize_patterns(findings[:3])
    print(f"    Recognized {len(patterns)} patterns")
    if patterns:
        print(f"    First pattern: {patterns[0].name}")
    
    # Test Optimization Analyzer
    print("\n3️⃣ Testing Optimization Analyzer...")
    from granger_hub.discovery.analysis import OptimizationAnalyzer
    analyzer = OptimizationAnalyzer()
    if patterns:
        score = await analyzer.analyze_pattern(patterns[0])
        print(f"    Optimization score: {score.overall_score:.2f}")
        print(f"    Bottlenecks: {len(score.bottlenecks)}")
    
    # Test Scenario Generator
    print("\n4️⃣ Testing Scenario Generator...")
    from granger_hub.discovery.generation import ScenarioGenerator
    generator = ScenarioGenerator()
    scenarios = await generator.generate_from_research(findings[:3], max_scenarios=1)
    print(f"    Generated {len(scenarios)} scenarios")
    if scenarios:
        print(f"    First scenario: {scenarios[0].name}")
    
    # Test Evolution Engine
    print("\n5️⃣ Testing Evolution Engine...")
    from granger_hub.discovery.learning import EvolutionEngine
    evolution = EvolutionEngine()
    insights = evolution.get_learning_insights()
    print(f"    Scenarios analyzed: {insights['total_scenarios_analyzed']}")
    print(f"    Learning progress: {insights['learning_progress']:.2f}")
    
    print("\n All components tested successfully!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run the Dynamic Interaction Discovery System"
    )
    parser.add_argument(
        "--mode",
        choices=["discovery", "test", "schedule"],
        default="discovery",
        help="Mode to run in"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        help="Research categories to focus on",
        choices=["optimization", "reliability", "security", "ml_patterns", "data_processing"]
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force fresh research (bypass cache)"
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=5,
        help="Maximum scenarios to generate"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logger.level("DEBUG")
    else:
        logger.level("INFO")
    
    # Run appropriate mode
    if args.mode == "test":
        asyncio.run(test_components())
    elif args.mode == "schedule":
        print(" Starting scheduled discovery...")
        orchestrator = DiscoveryOrchestrator()
        orchestrator.schedule_discovery()
        try:
            orchestrator.run_scheduler()
        except KeyboardInterrupt:
            print("\n Scheduler stopped")
    else:
        # Run discovery
        asyncio.run(run_discovery(
            categories=args.categories,
            force_refresh=args.force_refresh,
            max_scenarios=args.max_scenarios
        ))


if __name__ == "__main__":
    main()