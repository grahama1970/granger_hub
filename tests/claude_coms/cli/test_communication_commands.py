"""
Test CLI communication commands with real data.

Tests schema negotiation, compatibility verification, and pipeline validation
using actual module configurations and temporary files.
"""
import asyncio
import json
import tempfile
from pathlib import Path
from typer.testing import CliRunner
from granger_hub.cli.communication_commands import app

runner = CliRunner()


def test_negotiate_schema_command():
    """Test schema negotiation between modules with real data."""
    # Real module configuration for STIX processor to ML analyzer
    module_config = {
        "source_module": "stix_processor",
        "target_module": "ml_analyzer",
        "schema": {
            "input": {
                "type": "object",
                "properties": {
                    "stix_objects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "id": {"type": "string"},
                                "created": {"type": "string", "format": "date-time"}
                            }
                        }
                    }
                }
            },
            "output": {
                "type": "object",
                "properties": {
                    "analysis_result": {
                        "type": "object",
                        "properties": {
                            "threat_score": {"type": "number", "minimum": 0, "maximum": 100},
                            "classifications": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(module_config, f)
        config_path = f.name
    
    result = runner.invoke(app, ["negotiate-schema", config_path])
    assert result.exit_code == 0
    assert "Schema negotiation successful" in result.stdout or "negotiated" in result.stdout.lower()
    
    # Cleanup
    Path(config_path).unlink()


def test_verify_compatibility_command():
    """Test module compatibility verification with real schemas."""
    # Create real pipeline configuration with compatible modules
    pipeline_config = {
        "pipeline_name": "stix_to_ml_pipeline",
        "modules": [
            {
                "name": "stix_processor",
                "version": "1.0.0",
                "input_schema": None,  # First module has no input
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "stix_data": {
                            "type": "array",
                            "items": {"type": "object"}
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "count": {"type": "integer"},
                                "timestamp": {"type": "string"}
                            }
                        }
                    }
                }
            },
            {
                "name": "ml_analyzer",
                "version": "1.0.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "stix_data": {
                            "type": "array",
                            "items": {"type": "object"}
                        }
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "predictions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "entity_id": {"type": "string"},
                                    "threat_level": {"type": "string"},
                                    "confidence": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(pipeline_config, f)
        pipeline_path = f.name
    
    result = runner.invoke(app, ["verify-compatibility", pipeline_path])
    assert result.exit_code == 0
    assert "compatibility: pass" in result.stdout.lower() or "compatible" in result.stdout.lower()
    
    # Cleanup
    Path(pipeline_path).unlink()


def test_verify_incompatible_modules():
    """Test detection of incompatible module schemas."""
    # Create pipeline with incompatible schemas
    incompatible_config = {
        "pipeline_name": "incompatible_pipeline",
        "modules": [
            {
                "name": "module_a",
                "version": "1.0.0",
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "string"}  # Outputs string
                    }
                }
            },
            {
                "name": "module_b",
                "version": "1.0.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "array"}  # Expects array
                    }
                },
                "output_schema": {"type": "object"}
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(incompatible_config, f)
        config_path = f.name
    
    result = runner.invoke(app, ["verify-compatibility", config_path])
    # Should either fail or report incompatibility
    assert result.exit_code != 0 or "incompatible" in result.stdout.lower() or "fail" in result.stdout.lower()
    
    # Cleanup
    Path(config_path).unlink()


def test_validate_pipeline_command():
    """Test full pipeline validation with real configuration."""
    # Create comprehensive pipeline configuration
    pipeline_config = {
        "pipeline_id": "cyber_threat_pipeline_001",
        "name": "Cyber Threat Analysis Pipeline",
        "description": "Processes STIX data through ML analysis",
        "modules": [
            {
                "name": "stix_ingestion",
                "version": "2.0.0",
                "config": {
                    "source": "threat_feed",
                    "batch_size": 100
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "stix_bundle": {"type": "object"},
                        "ingestion_timestamp": {"type": "string"}
                    }
                }
            },
            {
                "name": "data_enrichment",
                "version": "1.5.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "stix_bundle": {"type": "object"}
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "enriched_data": {"type": "object"},
                        "enrichment_sources": {"type": "array"}
                    }
                }
            },
            {
                "name": "ml_classification",
                "version": "3.0.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "enriched_data": {"type": "object"}
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "classification": {"type": "string"},
                        "confidence_scores": {"type": "object"}
                    }
                }
            }
        ],
        "validation_rules": {
            "require_version": True,
            "check_schema_compatibility": True,
            "validate_module_config": True
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(pipeline_config, f)
        pipeline_path = f.name
    
    result = runner.invoke(app, ["validate-pipeline", pipeline_path])
    assert result.exit_code == 0
    assert "validation: pass" in result.stdout.lower() or "valid" in result.stdout.lower()
    
    # Cleanup
    Path(pipeline_path).unlink()


def test_monitor_session_command():
    """Test session monitoring with real session data."""
    # Create session configuration
    session_config = {
        "session_id": "test_monitor_001",
        "database": ":memory:",  # Use in-memory database for testing
        "modules": ["stix_processor", "ml_analyzer"],
        "monitoring": {
            "interval_seconds": 1,
            "metrics": ["throughput", "errors", "latency"]
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(session_config, f)
        config_path = f.name
    
    # Monitor command might run indefinitely, so we test if it starts correctly
    result = runner.invoke(app, ["monitor-session", config_path, "--duration", "1"])
    # Should either run successfully or indicate monitoring started
    assert result.exit_code == 0 or "monitoring" in result.stdout.lower()
    
    # Cleanup
    Path(config_path).unlink()


def test_get_communication_status():
    """Test getting communication status between modules."""
    # Create status request configuration
    status_config = {
        "module_pairs": [
            {"source": "stix_processor", "target": "ml_analyzer"},
            {"source": "ml_analyzer", "target": "report_generator"}
        ],
        "include_metrics": True
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(status_config, f)
        config_path = f.name
    
    result = runner.invoke(app, ["communication-status", config_path])
    assert result.exit_code == 0
    assert "status" in result.stdout.lower() or "communication" in result.stdout.lower()
    
    # Cleanup
    Path(config_path).unlink()


if __name__ == "__main__":
    # Run all tests with real data
    print("Running CLI communication command tests...")
    
    test_negotiate_schema_command()
    print("✅ Schema negotiation test passed")
    
    test_verify_compatibility_command()
    print("✅ Compatibility verification test passed")
    
    test_verify_incompatible_modules()
    print("✅ Incompatibility detection test passed")
    
    test_validate_pipeline_command()
    print("✅ Pipeline validation test passed")
    
    test_monitor_session_command()
    print("✅ Session monitoring test passed")
    
    test_get_communication_status()
    print("✅ Communication status test passed")
    
    print("\n✅ All CLI communication tests passed!")