#!/usr/bin/env python3
"""
Minimal test to verify self-improvement system functionality
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_coms.discovery.self_improvement_engine import SelfImprovementEngine


async def test_basic_functionality():
    """Test basic self-improvement functionality"""
    print("🧪 Testing Self-Improvement System - Basic Functionality\n")
    
    # Create engine with test workspace
    test_workspace = Path("/tmp/test_workspace")
    test_workspace.mkdir(exist_ok=True)
    
    # Create mock hub
    hub = test_workspace / "claude-module-communicator"
    hub.mkdir(exist_ok=True)
    (hub / "src").mkdir(exist_ok=True)
    (hub / "tests").mkdir(exist_ok=True)
    
    # Create mock spokes
    for spoke in ["marker", "sparta", "arangodb"]:
        spoke_dir = test_workspace / spoke
        spoke_dir.mkdir(exist_ok=True)
        (spoke_dir / "src").mkdir(exist_ok=True)
        (spoke_dir / "tests").mkdir(exist_ok=True)
    
    engine = SelfImprovementEngine(workspace_root=test_workspace)
    
    print("✅ Engine created successfully")
    
    # Test 1: Analyze ecosystem
    print("\n1️⃣ Testing ecosystem analysis...")
    try:
        analyses = await engine.analyze_ecosystem()
        print(f"   ✓ Analyzed {len(analyses)} projects")
        
        if "hub" in analyses:
            print(f"   ✓ Hub found: {analyses['hub'].project_name}")
        
        spoke_count = len([a for a in analyses if a != "hub"])
        print(f"   ✓ Found {spoke_count} spoke projects")
        
    except Exception as e:
        print(f"   ✗ Analysis failed: {e}")
        return False
    
    # Test 2: Create proposals
    print("\n2️⃣ Testing proposal generation...")
    try:
        # Create sample proposals
        integration_proposal = engine._create_integration_gap_proposal("marker", "arangodb")
        print(f"   ✓ Created integration proposal: {integration_proposal.id}")
        
        perf_proposal = engine._create_performance_improvement({
            "project": "test",
            "issue": "high_latency",
            "metric": 300
        })
        print(f"   ✓ Created performance proposal: {perf_proposal.id}")
        
        # Test prioritization
        engine.proposals = [integration_proposal, perf_proposal]
        prioritized = engine._prioritize_improvements(engine.proposals)
        
        print(f"   ✓ Prioritized {len(prioritized)} proposals")
        for p in prioritized:
            print(f"     - {p.id}: {p.priority} priority")
            
    except Exception as e:
        print(f"   ✗ Proposal generation failed: {e}")
        return False
    
    # Test 3: Generate task files
    print("\n3️⃣ Testing task file generation...")
    try:
        output_dir = test_workspace / "tasks"
        files = await engine.generate_improvement_tasks(output_dir)
        
        print(f"   ✓ Generated {len(files)} task files")
        for f in files[:3]:
            print(f"     - {f.name}")
            
        # Verify summary exists
        summary = output_dir / "IMPROVEMENT_PROPOSALS_SUMMARY.md"
        if summary.exists():
            print("   ✓ Summary file created")
            
    except Exception as e:
        print(f"   ✗ Task generation failed: {e}")
        return False
    
    print("\n✅ All basic tests passed!")
    return True


async def test_discovery_components():
    """Test discovery system components"""
    print("\n\n🔬 Testing Discovery System Components\n")
    
    # Test Research Agent
    print("1️⃣ Testing Research Agent...")
    try:
        from claude_coms.discovery.research import ResearchAgent
        agent = ResearchAgent()
        
        # Conduct minimal research
        findings = await agent.conduct_research(
            categories=["optimization"],
            force_refresh=True
        )
        
        print(f"   ✓ Found {len(findings)} research items")
        if findings:
            print(f"   ✓ First finding: {findings[0].title[:50]}...")
            
    except Exception as e:
        print(f"   ✗ Research failed: {e}")
        return False
    
    # Test Pattern Recognizer
    print("\n2️⃣ Testing Pattern Recognizer...")
    try:
        from claude_coms.discovery.analysis import PatternRecognizer
        recognizer = PatternRecognizer()
        
        patterns = await recognizer.recognize_patterns(findings[:1])
        print(f"   ✓ Recognized {len(patterns)} patterns")
        
    except Exception as e:
        print(f"   ✗ Pattern recognition failed: {e}")
        return False
    
    # Test Scenario Generator
    print("\n3️⃣ Testing Scenario Generator...")
    try:
        from claude_coms.discovery.generation import ScenarioGenerator
        generator = ScenarioGenerator()
        
        scenarios = await generator.generate_from_research(
            findings[:1],
            max_scenarios=1
        )
        
        print(f"   ✓ Generated {len(scenarios)} scenarios")
        if scenarios:
            print(f"   ✓ First scenario: {scenarios[0].name}")
            
    except Exception as e:
        print(f"   ✗ Scenario generation failed: {e}")
        return False
    
    print("\n✅ All discovery tests passed!")
    return True


async def main():
    """Run all tests"""
    print("="*60)
    print("Self-Improvement System Verification")
    print("="*60)
    
    # Test basic functionality
    basic_success = await test_basic_functionality()
    
    # Test discovery components
    discovery_success = await test_discovery_components()
    
    # Summary
    print("\n\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    if basic_success and discovery_success:
        print("✅ Self-Improvement System is fully operational!")
        print("\nThe system can:")
        print("- Analyze ecosystem projects")
        print("- Generate improvement proposals")
        print("- Create task files for review")
        print("- Discover new patterns from research")
        print("- Generate test scenarios automatically")
        print("\n🚀 Ready for continuous improvement!")
        return True
    else:
        print("❌ Some components need attention")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)