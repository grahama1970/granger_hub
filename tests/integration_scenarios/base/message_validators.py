"""
Message validation utilities for scenario testing
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))



from typing import Dict, Any, List, Optional, Set, Union
import json
from dataclasses import dataclass


@dataclass
class ValidationRule:
    """Defines a validation rule for messages"""
    field: str
    required: bool = True
    types: Optional[List[type]] = None
    values: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    custom: Optional[callable] = None


class MessageValidator:
    """Validates messages between modules"""
    
    def __init__(self):
        self.module_schemas: Dict[str, Dict[str, List[ValidationRule]]] = {}
        self.global_rules: List[ValidationRule] = []
    
    def add_module_schema(self, module_name: str, task_schemas: Dict[str, List[ValidationRule]]) -> None:
        """
        Add validation schema for a module's tasks
        
        Args:
            module_name: Name of the module
            task_schemas: Dict mapping task names to validation rules
        """
        self.module_schemas[module_name] = task_schemas
    
    def add_global_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule that applies to all messages"""
        self.global_rules.append(rule)
    
    def validate_message(
        self, 
        message: Dict[str, Any], 
        to_module: str,
        strict: bool = True
    ) -> tuple[bool, List[str]]:
        """
        Validate a message
        
        Args:
            message: Message content to validate
            to_module: Target module name
            strict: If True, fail on unknown fields
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Apply global rules
        for rule in self.global_rules:
            rule_errors = self._validate_field(message, rule)
            errors.extend(rule_errors)
        
        # Apply module-specific rules
        if to_module in self.module_schemas:
            task = message.get("task", "default")
            if task in self.module_schemas[to_module]:
                rules = self.module_schemas[to_module][task]
                for rule in rules:
                    rule_errors = self._validate_field(message, rule)
                    errors.extend(rule_errors)
            elif strict:
                errors.append(f"Unknown task '{task}' for module '{to_module}'")
        
        return len(errors) == 0, errors
    
    def _validate_field(self, message: Dict[str, Any], rule: ValidationRule) -> List[str]:
        """Validate a single field against a rule"""
        errors = []
        field_path = rule.field.split(".")
        
        # Navigate to the field
        value = message
        for part in field_path:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                if rule.required:
                    errors.append(f"Required field '{rule.field}' not found")
                return errors
        
        # Type validation
        if rule.types and type(value) not in rule.types:
            errors.append(f"Field '{rule.field}' has invalid type {type(value).__name__}, expected {[t.__name__ for t in rule.types]}")
        
        # Value validation
        if rule.values and value not in rule.values:
            errors.append(f"Field '{rule.field}' has invalid value '{value}', expected one of {rule.values}")
        
        # Numeric range validation
        if isinstance(value, (int, float)):
            if rule.min_value is not None and value < rule.min_value:
                errors.append(f"Field '{rule.field}' value {value} is below minimum {rule.min_value}")
            if rule.max_value is not None and value > rule.max_value:
                errors.append(f"Field '{rule.field}' value {value} is above maximum {rule.max_value}")
        
        # String/list length validation
        if isinstance(value, (str, list, dict)):
            length = len(value)
            if rule.min_length is not None and length < rule.min_length:
                errors.append(f"Field '{rule.field}' length {length} is below minimum {rule.min_length}")
            if rule.max_length is not None and length > rule.max_length:
                errors.append(f"Field '{rule.field}' length {length} is above maximum {rule.max_length}")
        
        # Pattern validation
        if rule.pattern and isinstance(value, str):
            import re
            if not re.match(rule.pattern, value):
                errors.append(f"Field '{rule.field}' value '{value}' does not match pattern '{rule.pattern}'")
        
        # Custom validation
        if rule.custom:
            try:
                if not rule.custom(value):
                    errors.append(f"Field '{rule.field}' failed custom validation")
            except Exception as e:
                errors.append(f"Field '{rule.field}' custom validation error: {str(e)}")
        
        return errors


class WorkflowValidator:
    """Validates entire workflows"""
    
    def __init__(self):
        self.message_validator = MessageValidator()
        self.workflow_rules: List[callable] = []
    
    def add_workflow_rule(self, rule: callable) -> None:
        """
        Add a rule that validates the entire workflow
        
        Args:
            rule: Function that takes workflow and returns (is_valid, errors)
        """
        self.workflow_rules.append(rule)
    
    def validate_workflow(self, workflow: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
        """
        Validate an entire workflow
        
        Args:
            workflow: List of workflow steps
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate individual messages
        for i, step in enumerate(workflow):
            if "to_module" in step and "content" in step:
                valid, msg_errors = self.message_validator.validate_message(
                    step["content"], 
                    step["to_module"]
                )
                if not valid:
                    errors.extend([f"Step {i}: {e}" for e in msg_errors])
        
        # Apply workflow-level rules
        for rule in self.workflow_rules:
            valid, rule_errors = rule(workflow)
            if not valid:
                errors.extend(rule_errors)
        
        return len(errors) == 0, errors


# Pre-defined validation rules for common patterns
class CommonValidators:
    """Common validation patterns"""
    
    @staticmethod
    def task_required() -> ValidationRule:
        """Task field is required"""
        return ValidationRule(field="task", required=True, types=[str])
    
    @staticmethod
    def pdf_path() -> ValidationRule:
        """PDF path validation"""
        return ValidationRule(
            field="pdf_path",
            required=True,
            types=[str],
            pattern=r".*\.pdf$",
            min_length=1
        )
    
    @staticmethod
    def page_number() -> ValidationRule:
        """Page number validation"""
        return ValidationRule(
            field="page_number",
            required=True,
            types=[int],
            min_value=1
        )
    
    @staticmethod
    def confidence_score() -> ValidationRule:
        """Confidence score validation"""
        return ValidationRule(
            field="confidence",
            required=False,
            types=[float],
            min_value=0.0,
            max_value=1.0
        )
    
    @staticmethod
    def output_format() -> ValidationRule:
        """Output format validation"""
        return ValidationRule(
            field="output_format",
            required=False,
            types=[str],
            values=["json", "markdown", "html", "pdf"]
        )
    
    @staticmethod
    def cwe_list() -> ValidationRule:
        """CWE list validation"""
        return ValidationRule(
            field="cwe_categories",
            required=False,
            types=[list],
            custom=lambda v: all(isinstance(x, str) and x.startswith("CWE-") for x in v)
        )
    
    @staticmethod
    def url_field(field_name: str = "url") -> ValidationRule:
        """URL validation"""
        return ValidationRule(
            field=field_name,
            required=True,
            types=[str],
            pattern=r"^https?://.*",
            min_length=10
        )
    
    @staticmethod
    def timestamp() -> ValidationRule:
        """Timestamp validation"""
        return ValidationRule(
            field="timestamp",
            required=False,
            types=[str, int, float]
        )


def create_standard_validator() -> MessageValidator:
    """Create a validator with standard rules"""
    validator = MessageValidator()
    
    # Add common global rules
    validator.add_global_rule(CommonValidators.task_required())
    
    # Add module-specific schemas
    validator.add_module_schema("marker", {
        "extract_pdf": [
            CommonValidators.pdf_path(),
            ValidationRule("extract_tables", required=False, types=[bool]),
            ValidationRule("extract_images", required=False, types=[bool])
        ],
        "extract_firmware_documentation": [
            CommonValidators.pdf_path(),
            ValidationRule("extract_code_blocks", required=True, types=[bool]),
            ValidationRule("extract_diagrams", required=True, types=[bool])
        ]
    })
    
    validator.add_module_schema("sparta", {
        "analyze_vulnerabilities": [
            ValidationRule("firmware_type", required=True, types=[str]),
            CommonValidators.cwe_list(),
            ValidationRule("check_mode", required=False, types=[str], values=["quick", "comprehensive"])
        ]
    })
    
    validator.add_module_schema("arxiv", {
        "search": [
            ValidationRule("query", required=True, types=[str], min_length=3),
            ValidationRule("max_results", required=False, types=[int], min_value=1, max_value=100)
        ]
    })
    
    return validator