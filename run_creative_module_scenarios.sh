#!/bin/bash

# Run Creative Module-Specific Scenarios
# These scenarios leverage actual modules like Marker, ArXiv, SPARTA, etc.

echo "Claude Module Communicator - Creative Module Scenarios"
echo "===================================================="
echo ""

# Function to run a scenario
run_scenario() {
    local scenario_name=$1
    local scenario_file=$2
    local description=$3
    
    echo "Running: $description"
    echo "Scenario: $scenario_name"
    echo "File: $scenario_file"
    python3 -m scenarios.$scenario_file
    echo "----------------------------------------"
    echo ""
}

# Check if specific scenario requested
if [ $# -eq 1 ]; then
    case $1 in
        # New Creative Module-Specific Scenarios
        "paper_validation")
            run_scenario "ScientificPaperValidation" "scientific_paper_validation_scenario" "Extract PDF with Marker, find supporting/refuting papers via ArXiv"
            ;;
        "nist_compliance")
            run_scenario "NISTCompliance" "nist_compliance_check_scenario" "Extract requirements with Marker, check NIST compliance via SPARTA"
            ;;
        "codebase_enhance")
            run_scenario "CodebaseEnhancement" "codebase_enhancement_scenario" "Analyze code, get improvements from YouTube/ArXiv, implement in branch"
            ;;
        "cwe_security")
            run_scenario "CWESecurity" "cwe_security_analysis_scenario" "Check code for CWE violations using SPARTA MITRE database"
            ;;
        "hardware_qa")
            run_scenario "HardwareQA" "hardware_verification_qa_scenario" "Extract tables with Marker, answer hardware verification questions"
            ;;
            
        "list")
            echo "Available Creative Module-Specific Scenarios:"
            echo ""
            echo "  paper_validation  - Extract PDF with Marker, validate with ArXiv papers"
            echo "  nist_compliance   - Check requirements against SPARTA NIST controls"
            echo "  codebase_enhance  - Full pipeline: analyze, research, implement, test, merge"
            echo "  cwe_security      - Analyze code for MITRE CWE violations"
            echo "  hardware_qa       - Extract hardware tables and verify specifications"
            echo ""
            echo "Usage: ./run_creative_module_scenarios.sh [scenario_name|all]"
            ;;
            
        "all")
            echo "Running all Creative Module-Specific scenarios..."
            echo ""
            run_scenario "ScientificPaperValidation" "scientific_paper_validation_scenario" "Extract PDF with Marker, find supporting/refuting papers via ArXiv"
            run_scenario "NISTCompliance" "nist_compliance_check_scenario" "Extract requirements with Marker, check NIST compliance via SPARTA"
            run_scenario "CodebaseEnhancement" "codebase_enhancement_scenario" "Analyze code, get improvements from YouTube/ArXiv, implement in branch"
            run_scenario "CWESecurity" "cwe_security_analysis_scenario" "Check code for CWE violations using SPARTA MITRE database"
            run_scenario "HardwareQA" "hardware_verification_qa_scenario" "Extract tables with Marker, answer hardware verification questions"
            ;;
            
        *)
            echo "Unknown scenario: $1"
            echo "Run './run_creative_module_scenarios.sh list' to see available scenarios"
            exit 1
            ;;
    esac
else
    echo "Creative Module-Specific Scenarios"
    echo ""
    echo "These scenarios leverage real modules:"
    echo "  - Marker (PDF extraction)"
    echo "  - ArXiv bot (paper search)"
    echo "  - SPARTA (security knowledge)"
    echo "  - YouTube transcripts"
    echo "  - Git operations"
    echo ""
    echo "Usage: ./run_creative_module_scenarios.sh [scenario_name|all|list]"
    echo ""
    echo "Examples:"
    echo "  ./run_creative_module_scenarios.sh paper_validation"
    echo "  ./run_creative_module_scenarios.sh nist_compliance"
    echo "  ./run_creative_module_scenarios.sh all"
fi
