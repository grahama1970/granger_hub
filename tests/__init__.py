"""
Tests Module
"""

from .conftest import pytest_configure, temp_dir, project_root
from .test_granger_integration import test_cli_has_granger_commands, test_generate_claude_commands, test_generate_mcp_config
from . import test_service_discovery
from .test_conversation_integration import DataProcessorModule, get_input_schema, get_output_schema
from .test_conversation_integration_mock import MockConversationManager, MockCommunicator, MockMessage
from .test_communicator_conversations import SimpleTestModule, get_input_schema, get_output_schema
from .test_honeypot import TestHoneypot, test_impossible_assertion, test_fake_network_call
from .test_arango_conversations_mock import MockArangoCollection, MockArangoDatabase, MockArangoConversationStore
from .test_integration_validation import TestIntegrationValidation, test_protocol_adapters_exist_and_work, ProducerModule
from .test_conversation_integration_simple import SimpleConversationModule, get_input_schema, get_output_schema
from .test_schema_negotiation import MarkerModule, ArangoModule, get_input_schema

__all__ = ["project_root", "test_generate_mcp_config", "test_service_discovery", "get_output_schema", "MockMessage", "get_output_schema", "test_fake_network_call", "MockArangoConversationStore", "ProducerModule", "get_output_schema", "get_input_schema"]
