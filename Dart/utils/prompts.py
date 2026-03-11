"""
Prompt template for the math grader.
"""
import re

PROMPT = """ 
    defult
"""

def build_math_prompt(question: str, answer: str, truth: str) -> str:
    """
    Builds the prompt for the math grader assistant.

    Args:
        question: The problem statement.
        answer: The student's answer.
        truth: The reference answer.

    Returns:
        The formatted prompt string.
    """
    return PROMPT.format(question=question, answer=answer, truth=truth)

def build_prompt(question: str, answer: str, truth: str) -> str:
    """
    Builds the prompt for the math grader assistant.

    Args:
        question: The problem statement.
        answer: The student's answer.
        truth: The reference answer.

    Returns:
        The formatted prompt string.
    """
def build_prompt(question: str, answer: str, truth: str) -> str:
    """
    Builds the prompt for the math grader assistant. (Legacy function)

    Args:
        question: The problem statement.
        answer: The student's answer.
        truth: The reference answer.

    Returns:
        The formatted prompt string.
    """
    return build_math_prompt(question, answer, truth)

def extract_boxed_answer(text: str) -> str:
    """
    Extract answer from LaTeX \\boxed{} format.
    
    Args:
        text: Text that may contain \\boxed{answer}
        
    Returns:
        Extracted answer or original text if no boxed format found
    """
    match = re.search(r'\\boxed\{([^}]+)\}', text)
    if match:
        return match.group(1)
    return text
