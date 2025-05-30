#!/usr/bin/env python3
"""
Simple test to verify scenarios can be loaded and structured correctly
"""

from scenarios.pdf_page_screenshot_scenario import PDFPageScreenshotScenario
from scenarios.table_detection_extraction_scenario import TableDetectionExtractionScenario
from scenarios.document_qa_scenario import DocumentQAScenario

def test_scenario(scenario_class):
    """Test a scenario class"""
    try:
        scenario = scenario_class()
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario.name}")
        print(f"Description: {scenario.description}")
        print(f"{'='*60}")
        
        # Test modules
        modules = scenario.setup_modules()
        print("\nModules:")
        for name, config in modules.items():
            print(f"  - {name}: {config['description']}")
        
        # Test workflow
        workflow = scenario.create_workflow()
        print(f"\nWorkflow ({len(workflow)} steps):")
        for i, msg in enumerate(workflow, 1):
            step = msg.metadata.get('step', msg.metadata.get('description', 'N/A')) if msg.metadata else 'N/A'
            print(f"  {i}. {msg.from_module} → {msg.to_module}: {step}")
        
        # Test JSON serialization
        json_data = scenario.to_json()
        print(f"\n✅ Scenario can be serialized to JSON ({len(json_data)} chars)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Practical Scenarios")
    print("=" * 80)
    
    scenarios = [
        PDFPageScreenshotScenario,
        TableDetectionExtractionScenario,
        DocumentQAScenario
    ]
    
    success_count = 0
    for scenario_class in scenarios:
        if test_scenario(scenario_class):
            success_count += 1
    
    print(f"\n{'='*80}")
    print(f"Summary: {success_count}/{len(scenarios)} scenarios passed validation")
    print(f"{'='*80}")
