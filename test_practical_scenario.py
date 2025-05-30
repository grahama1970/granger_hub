#!/usr/bin/env python3
"""
Test runner for practical scenarios
"""

import sys
import importlib.util

def test_scenario(scenario_name, module_name):
    """Test a specific scenario"""
    print(f"\n{'='*60}")
    print(f"Testing: {scenario_name}")
    print(f"{'='*60}\n")
    
    try:
        # Import the scenario module
        spec = importlib.util.spec_from_file_location(
            module_name, 
            f"scenarios/{module_name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the scenario class
        class_name = ''.join(word.capitalize() for word in module_name.split('_'))
        scenario_class = getattr(module, class_name)
        
        # Create and run the scenario
        scenario = scenario_class()
        print(f"Scenario: {scenario.name}")
        print(f"Description: {scenario.description}\n")
        
        # Show modules
        modules = scenario.setup_modules()
        print("Modules:")
        for name, config in modules.items():
            print(f"  - {name}: {config['description']}")
        
        # Show workflow
        print("\nWorkflow:")
        workflow = scenario.create_workflow()
        for i, msg in enumerate(workflow, 1):
            print(f"  {i}. {msg.from_module} → {msg.to_module}: {msg.metadata.get('step', 'N/A')}")
        
        print(f"\n✅ Scenario '{scenario_name}' structure validated successfully!")
        
    except Exception as e:
        print(f"\n❌ Error testing '{scenario_name}': {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test a few practical scenarios
    scenarios_to_test = [
        ("PDF Page Screenshot", "pdf_page_screenshot_scenario"),
        ("Table Detection & Extraction", "table_detection_extraction_scenario"),
        ("Document Q&A", "document_qa_scenario"),
    ]
    
    for name, module in scenarios_to_test:
        test_scenario(name, module)
    
    print(f"\n{'='*60}")
    print("All scenario structure tests completed!")
    print(f"{'='*60}")
