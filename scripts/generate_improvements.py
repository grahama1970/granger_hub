#!/usr/bin/env python3
"""
Generate improvement proposals for the Claude Module Communicator ecosystem

This script analyzes the hub and spoke projects to propose improvements.
"""

import asyncio
import sys
from pathlib import Path
import argparse
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from granger_hub.discovery.self_improvement_engine import SelfImprovementEngine, run_self_improvement
from loguru import logger


async def continuous_improvement_loop(interval_hours: int = 24):
    """Run continuous improvement analysis"""
    logger.info(f"🔄 Starting continuous improvement loop (every {interval_hours} hours)")
    
    while True:
        try:
            # Run improvement analysis
            await run_self_improvement()
            
            # Wait for next cycle
            logger.info(f"💤 Waiting {interval_hours} hours until next analysis...")
            await asyncio.sleep(interval_hours * 3600)
            
        except KeyboardInterrupt:
            logger.info("🛑 Stopping continuous improvement loop")
            break
        except Exception as e:
            logger.error(f"❌ Error in improvement loop: {e}")
            # Wait a bit before retrying
            await asyncio.sleep(300)  # 5 minutes


async def analyze_specific_integration(project1: str, project2: str):
    """Analyze specific integration between two projects"""
    logger.info(f"🔍 Analyzing integration: {project1} ↔ {project2}")
    
    engine = SelfImprovementEngine()
    
    # Create custom proposal for this integration
    proposal = engine._create_integration_gap_proposal(project1, project2)
    
    # Generate task file
    output_dir = Path("docs/tasks")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{proposal.id}_{proposal.title.replace(' ', '_').lower()}.md"
    filepath = output_dir / filename
    
    content = engine._generate_task_markdown(proposal)
    with open(filepath, 'w') as f:
        f.write(content)
    
    logger.info(f"✅ Generated integration proposal: {filepath}")
    
    return proposal


async def generate_performance_improvements():
    """Focus on performance improvements only"""
    logger.info("⚡ Generating performance improvement proposals")
    
    engine = SelfImprovementEngine()
    
    # Analyze ecosystem
    await engine.analyze_ecosystem()
    
    # Focus on performance
    bottlenecks = engine._analyze_performance_bottlenecks()
    proposals = []
    
    for bottleneck in bottlenecks:
        proposal = engine._create_performance_improvement(bottleneck)
        proposals.append(proposal)
    
    # Generate task files
    if proposals:
        engine.proposals = proposals
        task_files = await engine.generate_improvement_tasks()
        logger.info(f"✅ Generated {len(task_files)} performance improvement tasks")
    else:
        logger.info("✨ No performance issues found!")
    
    return proposals


async def check_improvement_status():
    """Check status of previous improvement proposals"""
    task_dir = Path("docs/tasks")
    if not task_dir.exists():
        logger.warning("No task directory found")
        return
    
    # Count tasks by status
    total_tasks = 0
    completed_tasks = 0
    
    for task_file in task_dir.glob("IMPROVE_*.md"):
        total_tasks += 1
        
        # Check if task has been completed (simple heuristic)
        with open(task_file, 'r') as f:
            content = f.read()
            if "**Status**: Completed" in content:
                completed_tasks += 1
    
    print(f"\n📊 Improvement Status:")
    print(f"Total Tasks: {total_tasks}")
    print(f"Completed: {completed_tasks}")
    print(f"Pending: {total_tasks - completed_tasks}")
    print(f"Completion Rate: {completed_tasks/total_tasks*100:.1f}%" if total_tasks > 0 else "N/A")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate improvement proposals for the ecosystem"
    )
    parser.add_argument(
        "--mode",
        choices=["single", "continuous", "performance", "integration", "status"],
        default="single",
        help="Mode to run in"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=24,
        help="Hours between improvement cycles (continuous mode)"
    )
    parser.add_argument(
        "--project1",
        help="First project for integration analysis"
    )
    parser.add_argument(
        "--project2",
        help="Second project for integration analysis"
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
    if args.mode == "continuous":
        asyncio.run(continuous_improvement_loop(args.interval))
    elif args.mode == "performance":
        asyncio.run(generate_performance_improvements())
    elif args.mode == "integration":
        if not args.project1 or not args.project2:
            print("Error: --project1 and --project2 required for integration mode")
            sys.exit(1)
        asyncio.run(analyze_specific_integration(args.project1, args.project2))
    elif args.mode == "status":
        asyncio.run(check_improvement_status())
    else:
        # Single run
        asyncio.run(run_self_improvement())


if __name__ == "__main__":
    main()