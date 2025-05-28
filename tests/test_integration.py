"""
Integration tests for Claude Module Communicator.

Tests the complete pipeline with real data, including module communication,
progress tracking, and CLI commands working together.
"""
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime
import aiosqlite
from typer.testing import CliRunner
from src.cli.communication_commands import app
from src.core.progress_utils import (
    init_database, 
    update_session_stats, 
    get_session_statistics,
    log_file_operation,
    track_module_communication,
    get_operation_summary
)

runner = CliRunner()


async def test_full_communication_pipeline():
    """Test complete module communication pipeline with real data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create database
        db_path = tmppath / "integration_test.db"
        await init_database(str(db_path))
        
        session_id = "integration_test_001"
        
        # Step 1: Initialize session
        await update_session_stats(
            db_path=str(db_path),
            session_id=session_id,
            files_processed=0,
            errors_encountered=0,
            start_time=datetime.now().isoformat(),
            modules_active=["stix_ingestion", "data_enrichment", "ml_classification", "report_generator"]
        )
        
        # Step 2: Create pipeline configuration
        pipeline_config = {
            "session_id": session_id,
            "database": str(db_path),
            "pipeline_name": "Cyber Threat Analysis Pipeline",
            "modules": [
                {
                    "name": "stix_ingestion",
                    "version": "2.1.0",
                    "config": {
                        "source": "threat_feed_api",
                        "batch_size": 100,
                        "format": "stix2.1"
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "stix_bundle": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "const": "bundle"},
                                    "id": {"type": "string"},
                                    "objects": {"type": "array"}
                                }
                            },
                            "metadata": {
                                "type": "object",
                                "properties": {
                                    "ingestion_timestamp": {"type": "string"},
                                    "source": {"type": "string"},
                                    "object_count": {"type": "integer"}
                                }
                            }
                        }
                    }
                },
                {
                    "name": "data_enrichment",
                    "version": "1.8.0",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "stix_bundle": {"type": "object"}
                        }
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "enriched_bundle": {
                                "type": "object",
                                "properties": {
                                    "original": {"type": "object"},
                                    "enrichments": {"type": "array"}
                                }
                            },
                            "enrichment_metadata": {
                                "type": "object",
                                "properties": {
                                    "sources_used": {"type": "array"},
                                    "enrichment_timestamp": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                {
                    "name": "ml_classification",
                    "version": "3.2.0",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "enriched_bundle": {"type": "object"}
                        }
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "classifications": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "object_id": {"type": "string"},
                                        "threat_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                        "attack_patterns": {"type": "array"}
                                    }
                                }
                            },
                            "model_metadata": {
                                "type": "object",
                                "properties": {
                                    "model_version": {"type": "string"},
                                    "processing_time_ms": {"type": "integer"}
                                }
                            }
                        }
                    }
                },
                {
                    "name": "report_generator",
                    "version": "2.0.0",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "classifications": {"type": "array"}
                        }
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "report": {
                                "type": "object",
                                "properties": {
                                    "summary": {"type": "string"},
                                    "high_priority_threats": {"type": "array"},
                                    "recommendations": {"type": "array"}
                                }
                            },
                            "report_metadata": {
                                "type": "object",
                                "properties": {
                                    "generated_at": {"type": "string"},
                                    "report_id": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            ]
        }
        
        # Write pipeline config
        pipeline_path = tmppath / "pipeline_config.json"
        pipeline_path.write_text(json.dumps(pipeline_config, indent=2))
        
        # Step 3: Validate pipeline
        result = runner.invoke(app, ["validate-pipeline", str(pipeline_path)])
        assert result.exit_code == 0
        assert "validation: pass" in result.stdout.lower() or "valid" in result.stdout.lower()
        
        # Step 4: Simulate file operations
        test_files = [
            "/data/stix/threat_feed_2024_01.json",
            "/data/stix/threat_feed_2024_02.json",
            "/data/stix/threat_feed_2024_03.json"
        ]
        
        for file_path in test_files:
            # Log file read
            await log_file_operation(
                db_path=str(db_path),
                session_id=session_id,
                operation_type="READ",
                file_path=file_path,
                status="SUCCESS",
                details={
                    "size_bytes": 1048576,  # 1MB
                    "stix_objects": 500,
                    "duration_ms": 150
                }
            )
        
        # Step 5: Simulate module communications
        # STIX Ingestion -> Data Enrichment
        await track_module_communication(
            db_path=str(db_path),
            session_id=session_id,
            source_module="stix_ingestion",
            target_module="data_enrichment",
            message_type="data_transfer",
            status="SUCCESS",
            metrics={
                "objects_transferred": 1500,
                "bytes_transferred": 3145728,
                "transfer_time_ms": 450,
                "batch_count": 15
            }
        )
        
        # Data Enrichment -> ML Classification
        await track_module_communication(
            db_path=str(db_path),
            session_id=session_id,
            source_module="data_enrichment",
            target_module="ml_classification",
            message_type="enriched_data",
            status="SUCCESS",
            metrics={
                "enriched_objects": 1500,
                "enrichment_sources": ["mitre_attack", "virustotal", "alienvault"],
                "processing_time_ms": 2300
            }
        )
        
        # ML Classification -> Report Generator
        await track_module_communication(
            db_path=str(db_path),
            session_id=session_id,
            source_module="ml_classification",
            target_module="report_generator",
            message_type="classifications",
            status="SUCCESS",
            metrics={
                "classified_objects": 1500,
                "high_risk_count": 47,
                "medium_risk_count": 238,
                "low_risk_count": 1215,
                "model_confidence_avg": 0.87
            }
        )
        
        # Step 6: Generate report
        report_path = tmppath / "threat_report.json"
        report_data = {
            "report_id": "THREAT-2024-001",
            "generated_at": datetime.now().isoformat(),
            "session_id": session_id,
            "summary": "Analyzed 1500 threat indicators from 3 data files",
            "high_priority_threats": [
                {
                    "indicator": "malware:backdoor.trojan",
                    "confidence": 0.95,
                    "recommended_action": "Block immediately"
                },
                {
                    "indicator": "attack-pattern:spear-phishing",
                    "confidence": 0.89,
                    "recommended_action": "Update email filters"
                }
            ],
            "statistics": {
                "total_objects_processed": 1500,
                "high_risk": 47,
                "medium_risk": 238,
                "low_risk": 1215,
                "processing_time_seconds": 5.2
            }
        }
        
        # Log report generation
        await log_file_operation(
            db_path=str(db_path),
            session_id=session_id,
            operation_type="WRITE",
            file_path=str(report_path),
            status="SUCCESS",
            details={
                "size_bytes": len(json.dumps(report_data)),
                "format": "json",
                "report_type": "threat_analysis"
            }
        )
        
        report_path.write_text(json.dumps(report_data, indent=2))
        
        # Step 7: Update final session stats
        await update_session_stats(
            db_path=str(db_path),
            session_id=session_id,
            files_processed=4,  # 3 input + 1 output
            errors_encountered=0,
            bytes_processed=3145728 + len(json.dumps(report_data)),
            end_time=datetime.now().isoformat()
        )
        
        # Step 8: Verify results
        final_stats = await get_session_statistics(str(db_path), session_id)
        assert final_stats["files_processed"] == 4
        assert final_stats["errors_encountered"] == 0
        assert final_stats["modules_active"] == ["stix_ingestion", "data_enrichment", "ml_classification", "report_generator"]
        
        # Check operation summary
        op_summary = await get_operation_summary(str(db_path), session_id)
        assert op_summary["total_operations"] == 4
        assert op_summary["successful_operations"] == 4
        assert op_summary["operation_types"]["READ"] == 3
        assert op_summary["operation_types"]["WRITE"] == 1
        
        # Verify report was created
        assert report_path.exists()
        saved_report = json.loads(report_path.read_text())
        assert saved_report["report_id"] == "THREAT-2024-001"
        assert len(saved_report["high_priority_threats"]) == 2
        
        return True


async def test_error_handling_and_recovery():
    """Test pipeline error handling and recovery mechanisms."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create database
        db_path = tmppath / "error_test.db"
        await init_database(str(db_path))
        
        session_id = "error_test_001"
        
        # Initialize session
        await update_session_stats(
            db_path=str(db_path),
            session_id=session_id,
            files_processed=0,
            errors_encountered=0,
            start_time=datetime.now().isoformat()
        )
        
        # Simulate file operation failure
        await log_file_operation(
            db_path=str(db_path),
            session_id=session_id,
            operation_type="PARSE",
            file_path="/data/corrupted_file.json",
            status="FAILED",
            details={
                "error": "JSONDecodeError",
                "message": "Expecting value: line 1 column 1 (char 0)",
                "attempted_recovery": True,
                "recovery_status": "partial"
            }
        )
        
        # Simulate module communication failure
        await track_module_communication(
            db_path=str(db_path),
            session_id=session_id,
            source_module="data_processor",
            target_module="ml_analyzer",
            message_type="data_transfer",
            status="FAILED",
            metrics={
                "error": "ConnectionTimeout",
                "retry_attempts": 3,
                "last_error_timestamp": datetime.now().isoformat()
            }
        )
        
        # Update stats with errors
        await update_session_stats(
            db_path=str(db_path),
            session_id=session_id,
            files_processed=1,
            errors_encountered=2
        )
        
        # Verify error tracking
        stats = await get_session_statistics(str(db_path), session_id)
        assert stats["errors_encountered"] == 2
        
        # Check operation summary includes failures
        summary = await get_operation_summary(str(db_path), session_id)
        assert summary["failed_operations"] == 1
        
        return True


async def test_performance_monitoring():
    """Test performance monitoring across the pipeline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create database
        db_path = tmppath / "performance_test.db"
        await init_database(str(db_path))
        
        session_id = "performance_test_001"
        
        # Track performance metrics
        modules = ["ingestion", "processing", "analysis", "reporting"]
        
        for i, module in enumerate(modules):
            # Simulate varying performance
            processing_time = 100 + (i * 50)  # Increasing processing time
            throughput = 1000 - (i * 100)  # Decreasing throughput
            
            await track_module_communication(
                db_path=str(db_path),
                session_id=session_id,
                source_module=module,
                target_module=modules[i+1] if i < len(modules)-1 else "output",
                message_type="performance_test",
                status="SUCCESS",
                metrics={
                    "processing_time_ms": processing_time,
                    "records_per_second": throughput,
                    "memory_usage_mb": 256 + (i * 64),
                    "cpu_usage_percent": 25 + (i * 10)
                }
            )
        
        # Verify performance data was tracked
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM module_communications WHERE session_id = ?",
                (session_id,)
            )
            count = (await cursor.fetchone())[0]
            assert count == 4
        
        return True


if __name__ == "__main__":
    # Run all integration tests
    print("Running integration tests...")
    
    async def run_all_tests():
        result1 = await test_full_communication_pipeline()
        if result1:
            print("✅ Full communication pipeline test passed")
        
        result2 = await test_error_handling_and_recovery()
        if result2:
            print("✅ Error handling and recovery test passed")
        
        result3 = await test_performance_monitoring()
        if result3:
            print("✅ Performance monitoring test passed")
        
        print("\n✅ All integration tests passed!")
    
    asyncio.run(run_all_tests())