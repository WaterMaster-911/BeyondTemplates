"""
JSON parsing utilities for LLM outputs.
"""
import json
import re
import pathlib
import datetime
from typing import Any

def parse_json_from_response(raw: str, sid: str = "unk") -> dict[str, Any]:
    """
    Extracts a JSON object from a raw string response from an LLM.

    Args:
        raw: The raw string response.
        sid: Sample ID for debugging purposes.

    Returns:
        A dictionary parsed from the JSON, with default values for robustness.
    """
    txt = re.sub(r'^```(?:json)?|```$', '', raw.strip(), flags=re.I)
    m = re.search(r'\{.*?\}', txt, re.S)
    try:
        d = json.loads(m.group()) if m else None
        if not isinstance(d, dict):
            raise ValueError("Parsed JSON is not a dictionary.")
        # Ensure essential keys are present with default values
        defaults = {"reasoning": "", "student_final_answer": "", "is_correct": False, "confidence": 0.0}
        return {**defaults, **d}
    except Exception as e:
        debug_dir = pathlib.Path("./debug_json_fail")
        debug_dir.mkdir(exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        (debug_dir / f"{sid}_{timestamp}.txt").write_text(txt, encoding='utf-8')
        return {
            "reasoning": str(e),
            "student_final_answer": "",
            "is_correct": False,
            "confidence": 0.0,
            "_parse_error": True
        }
