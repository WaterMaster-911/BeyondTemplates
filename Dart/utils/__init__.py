"""
Utils module containing all utility functions and components.
"""

# Schema definitions
from .schemas import (
    MATH_JUDGMENT_SCHEMA, DETAILED_JUDGMENT_SCHEMA, CODE_JUDGMENT_SCHEMA,
    get_schema_by_name
)

# JSON parsers
from .parsers import parse_json_from_response

# Prompt templates and utilities
from .prompts import MATH_GRADER_PROMPT, build_math_prompt, extract_boxed_answer

# Enhanced voting system
from .voting import (
    VoteAggregator, SimpleVoteAggregator, WeightedVoteAggregator, ConfidenceDistributionAggregator,
    ResultComputer, MajorityResultComputer, ThresholdResultComputer, WeightedResultComputer, 
    EnsembleResultComputer, EnhancedVotingStrategy
)

__all__ = [
    # Schemas
    'MATH_JUDGMENT_SCHEMA', 'DETAILED_JUDGMENT_SCHEMA', 'CODE_JUDGMENT_SCHEMA',
    'get_schema_by_name',
    
    # Parsers
    'extract_json_from_text',
    
    # Prompts
    'MATH_GRADER_PROMPT', 'build_math_prompt', 'extract_boxed_answer',
    
    # Voting
    'VoteAggregator', 'SimpleVoteAggregator', 'WeightedVoteAggregator', 'ConfidenceDistributionAggregator',
    'ResultComputer', 'MajorityResultComputer', 'ThresholdResultComputer', 'WeightedResultComputer',
    'EnsembleResultComputer', 'EnhancedVotingStrategy'
]
