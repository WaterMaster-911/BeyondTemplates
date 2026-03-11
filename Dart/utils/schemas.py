"""
Schema definitions for different judgment types.
"""
from typing import Dict, Any

# Basic judgment schema for math problems
MATH_JUDGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "1-2 sentences explaining the judgment"
        },
        "student_final_answer": {
            "type": "string", 
            "description": "The extracted final answer from student"
        },
        "is_correct": {
            "type": "boolean",
            "description": "Whether the answer is correct"
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence level (0.0-1.0)"
        }
    },
    "required": ["reasoning", "student_final_answer", "is_correct", "confidence"],
    "additionalProperties": False
}

# Detailed judgment schema with more fields
DETAILED_JUDGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "student_final_answer": {"type": "string"},
        "is_correct": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "error_type": {
            "type": "string",
            "enum": ["computational", "conceptual", "formatting", "none"],
            "description": "Type of error if incorrect"
        },
        "partial_credit": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Partial credit score"
        },
        "difficulty_assessment": {
            "type": "string",
            "enum": ["easy", "medium", "hard"],
            "description": "Assessed difficulty of the problem"
        }
    },
    "required": ["reasoning", "student_final_answer", "is_correct", "confidence"],
    "additionalProperties": False
}

# Code evaluation schema
CODE_JUDGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "is_correct": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "code_quality": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Code quality score"
        },
        "efficiency": {
            "type": "string",
            "enum": ["poor", "fair", "good", "excellent"],
            "description": "Efficiency assessment"
        },
        "style_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Code style score"
        }
    },
    "required": ["reasoning", "is_correct", "confidence"],
    "additionalProperties": False
}

def get_schema_by_name(name: str) -> Dict[str, Any]:
    """Get predefined schema by name."""
    schemas = {
        "basic": MATH_JUDGMENT_SCHEMA,
        "math": MATH_JUDGMENT_SCHEMA,
        "detailed": DETAILED_JUDGMENT_SCHEMA,
        "code": CODE_JUDGMENT_SCHEMA
    }
    return schemas.get(name, MATH_JUDGMENT_SCHEMA)
