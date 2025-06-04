#!/usr/bin/env python3
"""
Script to help migrate scenarios from /scenarios to /tests/integration_scenarios
"""

import os
import sys
from pathlib import Path
import ast
import textwrap

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


def analyze_scenario(scenario_path: Path) -> dict:
    """Analyze a scenario file and extract key information"""
    with open(scenario_path, 'r') as f:
        content = f.read()
    
    # Parse the AST
    tree = ast.parse(content)
    
    info = {
        'filename': scenario_path.name,
        'class_name': None,
        'description': None,
        'modules': [],
        'workflow_steps': 0,
        'category': 'general'
    }
    
    # Find the scenario class
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if any(base.id == 'ScenarioBase' for base in node.bases if hasattr(base, 'id')):
                info['class_name'] = node.name
                
                # Get docstring
                if ast.get_docstring(node):
                    info['description'] = ast.get_docstring(node)
                
                # Analyze methods
                for method in node.body:
                    if isinstance(method, ast.FunctionDef):
                        if method.name == 'setup_modules':
                            # Extract module names
                            for n in ast.walk(method):
                                if isinstance(n, ast.Str) and n.s not in info['modules']:
                                    # Simple heuristic for module names
                                    if '_' in n.s or n.s.islower():
                                        info['modules'].append(n.s)
                        
                        elif method.name == 'create_workflow':
                            # Count workflow steps
                            for n in ast.walk(method):
                                if isinstance(n, ast.Call):
                                    if hasattr(n.func, 'id') and n.func.id == 'Message':
                                        info['workflow_steps'] += 1
    
    # Determine category based on filename or content
    if 'security' in scenario_path.name.lower() or 'vulnerability' in scenario_path.name.lower():
        info['category'] = 'security'
    elif 'document' in scenario_path.name.lower() or 'pdf' in scenario_path.name.lower():
        info['category'] = 'document_processing'
    elif 'arxiv' in str(info['modules']) or 'youtube' in str(info['modules']):
        info['category'] = 'research_integration'
    elif 'llm' in str(info['modules']) or 'unsloth' in str(info['modules']):
        info['category'] = 'ml_workflows'
    elif 'arangodb' in str(info['modules']):
        info['category'] = 'knowledge_management'
    
    return info


def generate_test_template(scenario_info: dict) -> str:
    """Generate a test file template based on scenario info"""
    test_name = scenario_info['filename'].replace('_scenario.py', '')
    class_name = f"Test{scenario_info['class_name'].replace('Scenario', '')}"
    
    template = f'''"""
Test {test_name.replace('_', ' ')} scenarios

Migrated from: scenarios/{scenario_info['filename']}
Original description: {scenario_info['description']}
"""

import pytest
from tests.integration_scenarios.base.scenario_test_base import ScenarioTestBase, TestMessage
from tests.integration_scenarios.base.result_assertions import ScenarioAssertions


class {class_name}(ScenarioTestBase):
    """{scenario_info['description']}"""
    
    def register_modules(self):
        """Modules provided by fixtures"""
        # Original modules: {', '.join(scenario_info['modules'])}
        return {{}}
    
    def create_test_workflow(self):
        """Create test workflow"""
        # TODO: Migrate workflow from original scenario
        # Original had {scenario_info['workflow_steps']} steps
        return [
            # Add TestMessage objects here
        ]
    
    def assert_results(self, results):
        """Assert expected outcomes"""
        ScenarioAssertions.assert_workflow_completed(results, {scenario_info['workflow_steps']})
        # TODO: Add specific assertions based on scenario logic
    
    @pytest.mark.integration
    @pytest.mark.{scenario_info['category']}
    async def test_successful_workflow(self, mock_modules, workflow_runner):
        """Test successful execution"""
        # TODO: Setup mock responses for modules
        {generate_mock_setup(scenario_info['modules'])}
        
        workflow_runner.module_registry = mock_modules.mocks
        
        # Run scenario
        result = await self.run_scenario()
        
        # Assert success
        assert result["success"] is True
        self.assert_results(result["results"])
    
    @pytest.mark.integration
    @pytest.mark.{scenario_info['category']}
    async def test_with_failure(self, mock_modules, workflow_runner):
        """Test handling of module failure"""
        # TODO: Add failure test case
        pass
'''
    
    return template


def generate_mock_setup(modules: list) -> str:
    """Generate mock setup code for modules"""
    setup_lines = []
    for module in modules[:3]:  # First 3 modules as example
        setup_lines.append(f'''
        mock_modules.get_mock("{module}").set_response(
            "task_name",  # TODO: Update task name
            {{"status": "success", "data": "TODO"}}
        )''')
    
    if len(modules) > 3:
        setup_lines.append("\n        # TODO: Setup remaining modules")
    
    return ''.join(setup_lines)


def main():
    """Main migration helper"""
    scenarios_dir = project_root / "scenarios"
    test_dir = project_root / "tests" / "integration_scenarios" / "categories"
    
    print("Scenario Migration Helper")
    print("=" * 60)
    
    # Find all scenario files
    scenario_files = list(scenarios_dir.glob("*_scenario.py"))
    
    print(f"Found {len(scenario_files)} scenarios to migrate\n")
    
    migration_plan = []
    
    for scenario_file in scenario_files:
        info = analyze_scenario(scenario_file)
        
        # Determine target location
        target_dir = test_dir / info['category']
        target_file = target_dir / f"test_{scenario_file.stem.replace('_scenario', '')}.py"
        
        migration_plan.append({
            'source': scenario_file,
            'target': target_file,
            'info': info,
            'exists': target_file.exists()
        })
        
        print(f"📄 {scenario_file.name}")
        print(f"   Class: {info['class_name']}")
        print(f"   Modules: {', '.join(info['modules'][:3])}{'...' if len(info['modules']) > 3 else ''}")
        print(f"   Steps: {info['workflow_steps']}")
        print(f"   Category: {info['category']}")
        print(f"   Target: {target_file.relative_to(test_dir)}")
        print(f"   Status: {'✅ Already migrated' if target_file.exists() else '❌ Needs migration'}")
        print()
    
    # Generate migration templates
    print("\nGeneration Options:")
    print("1. Generate all missing test templates")
    print("2. Generate specific test template")
    print("3. Show migration checklist")
    print("4. Exit")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        # Generate all missing
        generated = 0
        for item in migration_plan:
            if not item['exists']:
                template = generate_test_template(item['info'])
                
                # Create directory if needed
                item['target'].parent.mkdir(parents=True, exist_ok=True)
                
                # Write template
                with open(item['target'], 'w') as f:
                    f.write(template)
                
                print(f"✅ Generated: {item['target'].name}")
                generated += 1
        
        print(f"\nGenerated {generated} test templates")
        print("Next steps:")
        print("1. Copy workflow logic from original scenarios")
        print("2. Set up appropriate mock responses")
        print("3. Add specific assertions")
        print("4. Test the migrations")
        
    elif choice == "2":
        # Generate specific
        print("\nAvailable scenarios to migrate:")
        unmigrated = [item for item in migration_plan if not item['exists']]
        for i, item in enumerate(unmigrated):
            print(f"{i+1}. {item['source'].name}")
        
        if unmigrated:
            idx = input("\nSelect scenario number: ").strip()
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(unmigrated):
                    item = unmigrated[idx]
                    template = generate_test_template(item['info'])
                    
                    # Show template
                    print(f"\nTemplate for {item['source'].name}:")
                    print("-" * 60)
                    print(template)
                    print("-" * 60)
                    
                    save = input("\nSave to file? (y/n): ").strip().lower()
                    if save == 'y':
                        item['target'].parent.mkdir(parents=True, exist_ok=True)
                        with open(item['target'], 'w') as f:
                            f.write(template)
                        print(f"✅ Saved to: {item['target']}")
            except (ValueError, IndexError):
                print("Invalid selection")
        else:
            print("All scenarios already migrated!")
    
    elif choice == "3":
        # Show checklist
        print("\nMigration Checklist:")
        print("=" * 60)
        for item in migration_plan:
            status = "✅" if item['exists'] else "⬜"
            print(f"{status} {item['source'].name} → {item['target'].name}")
        
        migrated = sum(1 for item in migration_plan if item['exists'])
        print(f"\nProgress: {migrated}/{len(migration_plan)} migrated")


if __name__ == "__main__":
    main()