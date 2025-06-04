#!/usr/bin/env python3
"""
Demo script to show the self-improvement system in action
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from granger_hub.discovery.self_improvement_engine import SelfImprovementEngine
from loguru import logger


async def demo_self_improvement():
    """Demonstrate the self-improvement system"""
    print("🎯 Claude Module Communicator Self-Improvement Demo")
    print("="*60)
    
    # Initialize engine
    engine = SelfImprovementEngine()
    
    # Step 1: Analyze current ecosystem
    print("\n1️⃣ Analyzing Ecosystem Projects...")
    print("-"*40)
    
    analyses = await engine.analyze_ecosystem()
    
    print(f"✅ Analyzed {len(analyses)} projects\n")
    
    # Show analysis for hub
    if "hub" in analyses:
        hub = analyses["hub"]
        print(f"📦 Hub: {hub.project_name}")
        print(f"   Test Coverage: {hub.test_coverage:.1%}")
        print(f"   Integration Points: {len(hub.integration_points)}")
        print(f"   Last Updated: {hub.last_commit.strftime('%Y-%m-%d')}")
    
    # Show a few spokes
    spoke_count = 0
    for name, analysis in analyses.items():
        if name != "hub" and spoke_count < 3:
            print(f"\n📦 Spoke: {analysis.project_name}")
            print(f"   Role: {analysis.role}")
            print(f"   Modules: {', '.join(analysis.modules_provided)}")
            spoke_count += 1
    
    # Step 2: Discover improvements
    print("\n\n2️⃣ Discovering Improvement Opportunities...")
    print("-"*40)
    
    # Mock some discovery results for demo
    engine.proposal_counter = 0
    
    # Create sample improvements
    improvements = []
    
    # Integration improvement
    integration_proposal = engine._create_integration_gap_proposal("marker", "arangodb")
    improvements.append(integration_proposal)
    
    # Performance improvement
    perf_bottleneck = {
        "project": "claude_max_proxy",
        "issue": "high_latency",
        "metric": 250
    }
    perf_proposal = engine._create_performance_improvement(perf_bottleneck)
    improvements.append(perf_proposal)
    
    # Pattern from discovery
    pattern_metadata = {
        "name": "Parallel Research Pattern",
        "modules": ["arxiv", "youtube_transcripts", "llm_call"],
        "description": "Parallel research from multiple sources",
        "optimization_notes": ["Reduces research time by 60%", "Improves coverage"]
    }
    pattern_proposal = engine._create_pattern_improvement(pattern_metadata)
    improvements.append(pattern_proposal)
    
    engine.proposals = improvements
    
    print(f"✅ Generated {len(improvements)} improvement proposals\n")
    
    # Show proposals
    for proposal in improvements:
        print(f"📋 {proposal.id}: {proposal.title}")
        print(f"   Priority: {proposal.priority}")
        print(f"   Category: {proposal.category}")
        print(f"   Effort: {proposal.estimated_effort}")
        print(f"   Benefits: {proposal.expected_benefits[0]}")
    
    # Step 3: Generate task files
    print("\n\n3️⃣ Generating Task Files...")
    print("-"*40)
    
    # Create demo output directory
    demo_dir = Path("docs/tasks/demo")
    demo_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate files
    for proposal in improvements[:2]:  # Just first 2 for demo
        filename = f"{proposal.id}_{proposal.title.replace(' ', '_').lower()}.md"
        filepath = demo_dir / filename
        
        content = engine._generate_task_markdown(proposal)
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"✅ Created: {filename}")
    
    # Show sample content
    print("\n📄 Sample Task File Content:")
    print("-"*40)
    
    sample_file = demo_dir / f"{improvements[0].id}_{improvements[0].title.replace(' ', '_').lower()}.md"
    if sample_file.exists():
        with open(sample_file, 'r') as f:
            lines = f.readlines()
            # Show first 20 lines
            for line in lines[:20]:
                print(line.rstrip())
            if len(lines) > 20:
                print("... (truncated)")
    
    # Summary
    print("\n\n4️⃣ Summary")
    print("-"*40)
    print(f"✅ System analyzed {len(analyses)} projects")
    print(f"✅ Generated {len(improvements)} improvement proposals")
    print(f"✅ Created task files in: docs/tasks/demo/")
    print(f"\n🎉 Self-improvement system is ready for continuous operation!")
    print(f"\n💡 Next steps:")
    print(f"   1. Review generated proposals")
    print(f"   2. Prioritize and assign tasks")
    print(f"   3. Set up cron for automation: ./scripts/setup_self_improvement_cron.sh")


if __name__ == "__main__":
    asyncio.run(demo_self_improvement())