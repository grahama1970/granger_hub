"""
Integration scenario: DARPA Crawl with Granger modules
Purpose: Demonstrate hub-and-spoke pattern for DARPA proposal generation

This scenario shows how DARPA Crawl uses other Granger modules via
granger_hub instead of duplicating their logic.
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))



import asyncio
import json
from pathlib import Path
from datetime import datetime

from granger_hub import ModuleCommunicator
from granger_hub.core.modules import ExternalLLMModule
from darpa_crawl.darpa_module import DARPACrawlModule


async def darpa_proposal_scenario():
    """Complete DARPA proposal generation workflow"""
    
    print("🚀 Starting DARPA Crawl Integration Scenario")
    
    # Initialize the hub
    comm = ModuleCommunicator()
    
    # Register modules (spokes)
    print("📦 Registering modules...")
    
    # DARPA Crawl module
    darpa_module = DARPACrawlModule(comm.registry)
    comm.register_module("darpa_crawl", darpa_module)
    
    # External LLM module for Claude/Gemini access
    llm_module = ExternalLLMModule(comm.registry)
    comm.register_module("external_llm", llm_module)
    
    # Start all modules
    await darpa_module.start()
    await llm_module.start()
    
    print("✅ Modules registered and started")
    
    # Step 1: Search for opportunities
    print("\n🔍 Searching for DARPA opportunities...")
    
    search_result = await comm.send_message(
        target="darpa_crawl",
        action="search_opportunities",
        keywords=["AI", "verification", "autonomous systems"],
        source="all",
        limit=5
    )
    
    if search_result["success"]:
        opportunities = search_result["opportunities"]
        print(f"Found {len(opportunities)} opportunities")
        
        if opportunities:
            # Pick first opportunity
            opp = opportunities[0]
            opp_id = opp.get("notice_id", opp.get("id"))
            print(f"\n📋 Selected: {opp.get('title')}")
            
            # Step 2: Analyze alignment with Granger
            print("\n🎯 Analyzing alignment with Granger capabilities...")
            
            # This will trigger capability analysis via other modules
            alignment_result = await comm.send_message(
                target="darpa_crawl",
                action="analyze_alignment",
                opportunity_id=opp_id
            )
            
            if alignment_result["success"]:
                alignment = alignment_result["alignment"]
                print(f"Alignment score: {alignment.get('score', 0):.2f}")
                print(f"Relevant modules: {', '.join(alignment.get('relevant_modules', []))}")
                
                # Step 3: Generate proposal if good alignment
                if alignment.get("score", 0) > 0.6:
                    print("\n📝 Generating proposal...")
                    
                    proposal_result = await comm.send_message(
                        target="darpa_crawl",
                        action="generate_proposal",
                        opportunity_id=opp_id
                    )
                    
                    if proposal_result["success"]:
                        proposal = proposal_result["proposal"]
                        print(f"\n✅ Proposal generated!")
                        print(f"Gemini Score: {proposal.get('gemini_score', 0)}/100")
                        print(f"Proposal ID: {proposal.get('id')}")
                        
                        # Save proposal
                        output_dir = Path("./integration_test_output")
                        output_dir.mkdir(exist_ok=True)
                        
                        with open(output_dir / f"{proposal['id']}.json", "w") as f:
                            json.dump(proposal, f, indent=2)
                            
                        print(f"Saved to: {output_dir / f'{proposal['id']}.json'}")
                        
                        # Use RL to evaluate the interaction
                        print("\n🧠 Using RL Commons to evaluate interaction quality...")
                        
                        rl_score = await comm.send_message(
                            target="rl_commons",
                            action="evaluate_interaction",
                            interaction_type="darpa_proposal_generation",
                            metrics={
                                "alignment_score": alignment.get("score", 0),
                                "gemini_score": proposal.get("gemini_score", 0),
                                "time_taken": 120,  # seconds
                                "modules_used": ["darpa_crawl", "external_llm", "capability_analyzer"]
                            }
                        )
                        
                        if rl_score.get("success"):
                            print(f"RL Interaction Score: {rl_score.get('score', 0):.2f}")
                            
                else:
                    print(f"\n⚠️ Alignment too low ({alignment.get('score', 0):.2f}), skipping proposal")
                    
    # Get final status
    print("\n📊 Getting DARPA Crawl status...")
    status = await comm.send_message(
        target="darpa_crawl",
        action="get_status"
    )
    
    if status["success"]:
        print(json.dumps(status["status"], indent=2))
        
    # Cleanup
    await llm_module.stop()
    await darpa_module.stop()
    
    print("\n✅ DARPA Crawl integration scenario completed!")


async def test_module_discovery():
    """Test that DARPA Crawl module can be discovered"""
    
    print("\n🔍 Testing module discovery...")
    
    comm = ModuleCommunicator()
    darpa_module = DARPACrawlModule(comm.registry)
    comm.register_module("darpa_crawl", darpa_module)
    
    # Discover modules
    modules = comm.discover_modules()
    
    if "darpa_crawl" in modules:
        print("✅ DARPA Crawl module discovered")
        schema = modules["darpa_crawl"].get_schema()
        print(f"Capabilities: {', '.join(schema['capabilities'])}")
    else:
        print("❌ DARPA Crawl module not found")
        

async def test_natural_language_task():
    """Test natural language task execution"""
    
    print("\n💬 Testing natural language task...")
    
    comm = ModuleCommunicator()
    
    # Register modules
    darpa_module = DARPACrawlModule(comm.registry)
    comm.register_module("darpa_crawl", darpa_module)
    
    llm_module = ExternalLLMModule(comm.registry)
    comm.register_module("external_llm", llm_module)
    
    await darpa_module.start()
    await llm_module.start()
    
    # Execute natural language task
    result = await comm.execute_task(
        instruction="Find DARPA opportunities related to AI verification and analyze the top one",
        parameters={"max_results": 3}
    )
    
    print(f"Task result: {json.dumps(result, indent=2)}")
    
    await darpa_module.stop()
    await llm_module.stop()


if __name__ == "__main__":
    # Run all scenarios
    asyncio.run(darpa_proposal_scenario())
    asyncio.run(test_module_discovery())
    asyncio.run(test_natural_language_task())
