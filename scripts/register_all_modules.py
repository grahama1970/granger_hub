#!/usr/bin/env python3
"""Register all companion modules in the claude-module-communicator."""

import json
from pathlib import Path
from datetime import datetime

# Define all modules with their capabilities and schemas
MODULES = {
    "sparta": {
        "name": "sparta",
        "display_name": "SPARTA - Space Cybersecurity Data Ingestion",
        "system_prompt": "I am SPARTA, a cybersecurity data ingestion and enrichment system. I download, enrich, and prepare cybersecurity resources for processing.",
        "capabilities": [
            "data_ingestion",
            "stix_parsing",
            "resource_download",
            "metadata_enrichment",
            "pdf_collection",
            "html_collection"
        ],
        "output_schema": {
            "type": "object",
            "properties": {
                "resources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "type": {"type": "string", "enum": ["pdf", "html", "json"]},
                            "metadata": {"type": "object"},
                            "enrichment": {"type": "object"}
                        }
                    }
                },
                "batch_id": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"}
            }
        },
        "status": "active",
        "mcp_endpoint": "sparta.mcp"
    },
    "marker": {
        "name": "marker",
        "display_name": "Marker - Advanced PDF Processing",
        "system_prompt": "I am Marker, an advanced PDF document processor. I convert PDFs to structured markdown with AI-powered enhancements for accuracy.",
        "capabilities": [
            "pdf_to_markdown",
            "table_extraction",
            "section_detection",
            "image_extraction",
            "math_processing",
            "ai_enhancement",
            "batch_processing"
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "batch_id": {"type": "string"},
                "options": {
                    "type": "object",
                    "properties": {
                        "claude_features": {"type": "array"},
                        "output_format": {"type": "string"}
                    }
                }
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "sections": {"type": "array"},
                        "tables": {"type": "array"},
                        "images": {"type": "array"}
                    }
                },
                "processing_time": {"type": "number"}
            }
        },
        "status": "active",
        "mcp_endpoint": "marker.mcp"
    },
    "arangodb": {
        "name": "arangodb",
        "display_name": "ArangoDB Memory Bank",
        "system_prompt": "I am ArangoDB Memory Bank, a knowledge management system. I store conversations, create knowledge graphs, and generate Q&A pairs for fine-tuning.",
        "capabilities": [
            "memory_storage",
            "graph_creation",
            "semantic_search",
            "qa_generation",
            "contradiction_detection",
            "community_detection",
            "knowledge_graph",
            "batch_processing"
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "documents": {"type": "array"},
                "operation": {
                    "type": "string",
                    "enum": ["store", "query", "generate_qa", "analyze"]
                },
                "options": {"type": "object"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "qa_pairs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "answer": {"type": "string"},
                            "context": {"type": "string"},
                            "metadata": {"type": "object"}
                        }
                    }
                },
                "graph_data": {"type": "object"},
                "operation_result": {"type": "object"}
            }
        },
        "status": "active",
        "mcp_endpoint": "arangodb.mcp"
    },
    "youtube_transcripts": {
        "name": "youtube_transcripts",
        "display_name": "YouTube Transcripts Analysis",
        "system_prompt": "I am YouTube Transcripts Analysis tool. I search, fetch, and analyze YouTube video transcripts with advanced search capabilities.",
        "capabilities": [
            "youtube_search",
            "transcript_fetch",
            "full_text_search",
            "progressive_widening",
            "channel_analysis",
            "scientific_extraction",
            "batch_processing"
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "operation": {
                    "type": "string",
                    "enum": ["search", "fetch", "analyze", "extract"]
                },
                "options": {
                    "type": "object",
                    "properties": {
                        "channels": {"type": "array"},
                        "date_range": {"type": "object"}
                    }
                }
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "transcripts": {"type": "array"},
                "metadata": {"type": "object"},
                "analysis": {"type": "object"}
            }
        },
        "status": "active",
        "mcp_endpoint": "youtube_transcripts.mcp"
    },
    "llm_call": {
        "name": "llm_call",
        "display_name": "LLM Call - Universal LLM Interface",
        "system_prompt": "I am LLM Call, a universal interface for any LLM. I provide validated responses with intelligent retries across multiple providers.",
        "capabilities": [
            "multi_provider",
            "response_validation",
            "intelligent_retry",
            "model_selection",
            "prompt_optimization",
            "batch_processing"
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "model": {"type": "string"},
                "validation_schema": {"type": "object"},
                "options": {"type": "object"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "model_used": {"type": "string"},
                "validation_passed": {"type": "boolean"},
                "metadata": {"type": "object"}
            }
        },
        "status": "active",
        "mcp_endpoint": "llm_call.mcp"
    },
    "claude_test_reporter": {
        "name": "claude_test_reporter",
        "display_name": "Claude Test Reporter",
        "system_prompt": "I am Claude Test Reporter, a universal test reporting engine. I generate beautiful HTML reports and track test history across projects.",
        "capabilities": [
            "test_reporting",
            "html_generation",
            "history_tracking",
            "multi_project_dashboard",
            "flaky_detection",
            "trend_analysis"
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "test_results": {"type": "array"},
                "project_name": {"type": "string"},
                "report_type": {
                    "type": "string",
                    "enum": ["simple", "detailed", "dashboard", "history"]
                }
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "report_path": {"type": "string"},
                "summary": {"type": "object"},
                "trends": {"type": "object"}
            }
        },
        "status": "active",
        "mcp_endpoint": "claude_test_reporter.mcp"
    },
    "unsloth": {
        "name": "unsloth",
        "display_name": "Unsloth Enhanced Training",
        "system_prompt": "I am Unsloth, a LoRA adapter training system with student-teacher enhancement. I fine-tune models using Q&A data with Claude as teacher.",
        "capabilities": [
            "lora_training",
            "student_teacher",
            "model_validation",
            "huggingface_upload",
            "runpod_integration",
            "batch_processing"
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "qa_pairs": {"type": "array"},
                "model_name": {"type": "string"},
                "training_config": {"type": "object"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "adapter_path": {"type": "string"},
                "huggingface_url": {"type": "string"},
                "metrics": {"type": "object"},
                "validation_results": {"type": "object"}
            }
        },
        "status": "active",
        "mcp_endpoint": "unsloth.mcp"
    }
}

def register_modules():
    """Register all modules in the registry."""
    registry_path = Path("module_registry.json")
    
    # Load existing registry if it exists
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    else:
        registry = {}
    
    # Add timestamp to all modules
    timestamp = datetime.now().isoformat()
    for module_id, module_data in MODULES.items():
        module_data["last_seen"] = timestamp
        module_data["registered_at"] = timestamp
        registry[module_id] = module_data
    
    # Save updated registry
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=4)
    
    print(f"Successfully registered {len(MODULES)} modules:")
    for module_id in MODULES:
        print(f"  - {module_id}: {MODULES[module_id]['display_name']}")

if __name__ == "__main__":
    register_modules()
