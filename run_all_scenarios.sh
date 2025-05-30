#!/bin/bash

# Run All Scenarios Script
# Includes both creative complex scenarios and simple practical scenarios

echo "Claude Module Communicator - Scenario Runner"
echo "========================================="
echo ""

# Function to run a scenario
run_scenario() {
    local scenario_name=$1
    local scenario_file=$2
    local description=$3
    
    echo "Running: $description"
    echo "Scenario: $scenario_name"
    echo "File: $scenario_file"
    python -m scenarios.$scenario_file
    echo "----------------------------------------"
    echo ""
}

# Check if specific scenario requested
if [ $# -eq 1 ]; then
    case $1 in
        # Creative Scenarios
        "symphony")
            run_scenario "DataSymphony" "data_symphony_scenario" "Multi-stage data transformation symphony"
            ;;
        "web_scraper")
            run_scenario "WebScraper" "intelligent_web_scraper_scenario" "Intelligent web scraping orchestra"
            ;;
        "story_builder")
            run_scenario "StoryBuilder" "collaborative_story_builder_scenario" "Collaborative story creation"
            ;;
        "debate")
            run_scenario "DebateClub" "debate_club_scenario" "Multi-perspective debate simulation"
            ;;
        "game_master")
            run_scenario "GameMaster" "game_master_scenario" "Interactive game orchestration"
            ;;
        "creative_jam")
            run_scenario "CreativeJam" "creative_jam_scenario" "Real-time creative collaboration"
            ;;
        "time_machine")
            run_scenario "TimeMachine" "time_machine_scenario" "Historical data transformation"
            ;;
        "research_consensus")
            run_scenario "ResearchConsensus" "research_consensus_scenario" "Multi-agent consensus building"
            ;;
        "dynamic_explorer")
            run_scenario "DynamicExplorer" "dynamic_explorer_scenario" "Adaptive topic exploration"
            ;;
        "training_pipeline")
            run_scenario "TrainingPipeline" "research_training_pipeline_scenario" "Cross-domain knowledge transfer"
            ;;
            
        # Simple Practical Scenarios
        "pdf_screenshot")
            run_scenario "PDFScreenshot" "pdf_page_screenshot_scenario" "Navigate to PDF page and screenshot"
            ;;
        "table_extract")
            run_scenario "TableExtraction" "table_detection_extraction_scenario" "Detect and extract tables with confidence check"
            ;;
        "document_qa")
            run_scenario "DocumentQA" "document_qa_scenario" "Answer questions about document content"
            ;;
        "multi_step")
            run_scenario "MultiStep" "multi_step_processing_scenario" "Complete document processing workflow"
            ;;
        "info_extract")
            run_scenario "InfoExtraction" "info_extraction_scenario" "Extract structured information from documents"
            ;;
        "doc_compare")
            run_scenario "DocCompare" "document_comparison_scenario" "Compare two document versions"
            ;;
        "data_validate")
            run_scenario "DataValidation" "data_validation_scenario" "Validate extracted data against rules"
            ;;
            
        "list")
            echo "Available scenarios:"
            echo ""
            echo "CREATIVE SCENARIOS:"
            echo "  symphony          - Multi-stage data transformation symphony"
            echo "  web_scraper       - Intelligent web scraping orchestra"
            echo "  story_builder     - Collaborative story creation"
            echo "  debate            - Multi-perspective debate simulation"
            echo "  game_master       - Interactive game orchestration"
            echo "  creative_jam      - Real-time creative collaboration"
            echo "  time_machine      - Historical data transformation"
            echo "  research_consensus - Multi-agent consensus building"
            echo "  dynamic_explorer  - Adaptive topic exploration"
            echo "  training_pipeline - Cross-domain knowledge transfer"
            echo ""
            echo "PRACTICAL SCENARIOS:"
            echo "  pdf_screenshot    - Navigate to PDF page and screenshot"
            echo "  table_extract     - Detect and extract tables with confidence check"
            echo "  document_qa       - Answer questions about document content"
            echo "  multi_step        - Complete document processing workflow"
            echo "  info_extract      - Extract structured information from documents"
            echo "  doc_compare       - Compare two document versions"
            echo "  data_validate     - Validate extracted data against rules"
            echo ""
            echo "Usage: ./run_all_scenarios.sh [scenario_name|all|creative|practical]"
            ;;
            
        "creative")
            echo "Running all CREATIVE scenarios..."
            echo ""
            run_scenario "DataSymphony" "data_symphony_scenario" "Multi-stage data transformation symphony"
            run_scenario "WebScraper" "intelligent_web_scraper_scenario" "Intelligent web scraping orchestra"
            run_scenario "StoryBuilder" "collaborative_story_builder_scenario" "Collaborative story creation"
            run_scenario "DebateClub" "debate_club_scenario" "Multi-perspective debate simulation"
            run_scenario "GameMaster" "game_master_scenario" "Interactive game orchestration"
            run_scenario "CreativeJam" "creative_jam_scenario" "Real-time creative collaboration"
            run_scenario "TimeMachine" "time_machine_scenario" "Historical data transformation"
            run_scenario "ResearchConsensus" "research_consensus_scenario" "Multi-agent consensus building"
            run_scenario "DynamicExplorer" "dynamic_explorer_scenario" "Adaptive topic exploration"
            run_scenario "TrainingPipeline" "research_training_pipeline_scenario" "Cross-domain knowledge transfer"
            ;;
            
        "practical")
            echo "Running all PRACTICAL scenarios..."
            echo ""
            run_scenario "PDFScreenshot" "pdf_page_screenshot_scenario" "Navigate to PDF page and screenshot"
            run_scenario "TableExtraction" "table_detection_extraction_scenario" "Detect and extract tables with confidence check"
            run_scenario "DocumentQA" "document_qa_scenario" "Answer questions about document content"
            run_scenario "MultiStep" "multi_step_processing_scenario" "Complete document processing workflow"
            run_scenario "InfoExtraction" "info_extraction_scenario" "Extract structured information from documents"
            run_scenario "DocCompare" "document_comparison_scenario" "Compare two document versions"
            run_scenario "DataValidation" "data_validation_scenario" "Validate extracted data against rules"
            ;;
            
        "all")
            echo "Running ALL scenarios (Creative + Practical)..."
            echo ""
            $0 creative
            echo ""
            echo "========================================="
            echo ""
            $0 practical
            ;;
            
        *)
            echo "Unknown scenario: $1"
            echo "Run './run_all_scenarios.sh list' to see available scenarios"
            exit 1
            ;;
    esac
else
    echo "Claude Module Communicator - Scenario Runner"
    echo ""
    echo "Usage: ./run_all_scenarios.sh [scenario_name|all|creative|practical|list]"
    echo ""
    echo "Examples:"
    echo "  ./run_all_scenarios.sh pdf_screenshot   # Run PDF screenshot scenario"
    echo "  ./run_all_scenarios.sh practical        # Run all practical scenarios"
    echo "  ./run_all_scenarios.sh creative         # Run all creative scenarios"
    echo "  ./run_all_scenarios.sh all              # Run everything"
    echo "  ./run_all_scenarios.sh list             # Show all available scenarios"
fi
