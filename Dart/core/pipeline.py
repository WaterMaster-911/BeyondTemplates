"""
Simplified and elegant judging framework with clean abstractions.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional, Tuple, NamedTuple
from dataclasses import dataclass
import logging

class DataTuple(NamedTuple):
    """Intermediate data structure to hold key information for each sample."""
    sample_id: str
    question: str
    answer: str
    truth: str
    metadata: Dict[str, Any] = {}

class PromptBuilder(ABC):
    """Abstract prompt builder interface."""
    
    @abstractmethod
    def build(self, data: DataTuple) -> str:
        """Build prompt from data tuple."""
        pass

class DataMapper(ABC):
    """Abstract data mapper interface."""
    
    @abstractmethod
    def map(self, raw_sample: Dict[str, Any]) -> DataTuple:
        """Map raw JSON sample to DataTuple."""
        pass

class ResponseParser(ABC):
    """Abstract response parser interface."""
    
    @abstractmethod
    def parse(self, raw_response: str, data: DataTuple) -> Dict[str, Any]:
        """Parse LLM response into structured result."""
        pass

class VoteLogic(ABC):
    """Abstract vote logic interface."""
    
    @abstractmethod
    def vote(self, results: List[Dict[str, Any]], data: DataTuple) -> Dict[str, Any]:
        """Apply voting logic to multiple results."""
        pass

@dataclass
class JudgingPipeline:
    """Simple and elegant judging pipeline."""
    
    prompt_builder: PromptBuilder
    data_mapper: DataMapper
    response_parser: ResponseParser
    vote_logic: VoteLogic
    client: Any  # LLM client
    
    def __post_init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def judge_sample(self, raw_sample: Dict[str, Any], repeat: int = 1) -> Dict[str, Any]:
        """Judge a single sample with optional repetition."""
        
        try:
            # Step 1: Map raw data to intermediate tuple
            data = self.data_mapper.map(raw_sample)
            
            # Step 2: Build prompt
            prompt = self.prompt_builder.build(data)
            
            # Step 3: Get LLM responses (single or multiple)
            if repeat <= 1:
                raw_response = self.client.make_request(prompt, data.sample_id)
                result = self.response_parser.parse(raw_response, data)
            else:
                # Multiple requests for voting
                raw_responses = []
                for i in range(repeat):
                    response = self.client.make_request(prompt, f"{data.sample_id}_r{i}")
                    raw_responses.append(response)
                
                # Parse all responses
                parsed_results = []
                for i, raw_response in enumerate(raw_responses):
                    parsed = self.response_parser.parse(raw_response, data)
                    parsed_results.append(parsed)
                
                # Apply voting logic
                result = self.vote_logic.vote(parsed_results, data)
            
            return result
            
        except Exception as e:
            # Handle any errors during processing
            self._logger.error(f"Error judging sample {raw_sample.get('id', 'unknown')}: {str(e)}")
            
            # Return default error response
            return {
                "reasoning": f"Error during processing: {str(e)}",
                "student_final_answer": "",
                "is_correct": False,
                "confidence": 0.0,
                "_error": True,
                "_sample_id": raw_sample.get('id', 'unknown')
            }
    
    def judge_batch(self, samples: List[Dict[str, Any]], repeat: int = 1) -> List[Dict[str, Any]]:
        """Judge a batch of samples."""
        results = []
        for sample in samples:
            result = self.judge_sample(sample, repeat)
            results.append(result)
        return results

# ============================================================================
# Concrete Implementations
# ============================================================================

class MathPromptBuilder(PromptBuilder):
    """Math grading prompt builder."""
    
    def __init__(self, template: str = None):
        self.template = template or self._default_template()
    
    def build(self, data: DataTuple) -> str:
        return self.template.format(
            question=data.question,
            answer=data.answer,
            truth=data.truth
        )
    
    def _default_template(self) -> str:
        return """ _default_template """

class StandardDataMapper(DataMapper):
    """Standard data mapper for common JSON formats."""
    
    def __init__(self, 
                 id_key: str = "id",
                 question_key: str = "input", 
                 answer_key: str = "output",
                 truth_key: str = "gt",
                 extract_boxed: bool = False):
        self.id_key = id_key
        self.question_key = question_key
        self.answer_key = answer_key
        self.truth_key = truth_key
        self.extract_boxed = extract_boxed
    
    def map(self, raw_sample: Dict[str, Any]) -> DataTuple:
        sample_id = str(raw_sample.get(self.id_key, "unknown"))
        question = raw_sample.get(self.question_key, "")
        answer = raw_sample.get(self.answer_key, "")
        truth = raw_sample.get(self.truth_key, "")
        
        # Optional boxed answer extraction
        if self.extract_boxed:
            answer = self._extract_boxed(answer)
        
        metadata = {k: v for k, v in raw_sample.items() 
                   if k not in [self.id_key, self.question_key, self.answer_key, self.truth_key]}
        
        return DataTuple(
            sample_id=sample_id,
            question=question,
            answer=answer,
            truth=truth,
            metadata=metadata
        )
    
    def _extract_boxed(self, text: str) -> str:
        """Extract boxed answer if present."""
        import re
        match = re.search(r'\\boxed{([^}]*)}', text)
        return match.group(1) if match else text

class JsonResponseParser(ResponseParser):
    """JSON response parser with robust error handling."""
    
    def __init__(self, default_values: Dict[str, Any] = None):
        self.default_values = default_values or {
            "reasoning": "Failed to parse",
            "student_final_answer": "",
            "is_correct": False,
            "confidence": 0.0
        }
    
    def parse(self, raw_response: str, data: DataTuple) -> Dict[str, Any]:
        """Parse JSON response with fallback."""
        import json
        import re
        
        # Try to extract JSON from response
        try:
            # Clean up response
            cleaned = re.sub(r'^```(?:json)?|```$', '', raw_response.strip(), flags=re.I)
            json_match = re.search(r'\{.*?\}', cleaned, re.DOTALL)
            
            if json_match:
                parsed = json.loads(json_match.group())
                if isinstance(parsed, dict):
                    # Merge with defaults
                    result = {**self.default_values, **parsed}
                    result['_sample_id'] = data.sample_id
                    return result
            
            raise ValueError("No valid JSON found")
            
        except Exception as e:
            # Return default with error info
            return {
                **self.default_values,
                "reasoning": f"Parse error: {str(e)}",
                "_parse_error": True,
                "_sample_id": data.sample_id
            }

class SimpleVoteLogic(VoteLogic):
    """Simple majority vote logic."""
    
    def __init__(self, vote_key: str = "is_correct"):
        self.vote_key = vote_key
    
    def vote(self, results: List[Dict[str, Any]], data: DataTuple) -> Dict[str, Any]:
        if not results:
            return {"reasoning": "No results", "is_correct": False, "confidence": 0.0}
        
        votes = [r.get(self.vote_key, False) for r in results]
        positive_votes = votes.count(True)
        majority_decision = positive_votes > len(votes) // 2
        
        # Find representative result
        representative = next(
            (r for r in results if r.get(self.vote_key) == majority_decision),
            results[0]
        )
        
        # Add voting metadata
        representative = representative.copy()
        representative.update({
            self.vote_key: majority_decision,
            "voting_info": {
                "total_votes": len(votes),
                "positive_votes": positive_votes,
                "vote_ratio": f"{positive_votes}/{len(votes)}",
                "all_votes": votes
            }
        })
        
        return representative


class ConfidenceVoteLogic(VoteLogic):
    """Confidence-weighted voting logic"""
    
    def __init__(self, vote_key: str = "is_correct", confidence_key: str = "confidence"):
        self.vote_key = vote_key
        self.confidence_key = confidence_key
    
    def vote(self, results: List[Dict[str, Any]], data: DataTuple) -> Dict[str, Any]:
        if not results:
            return {"reasoning": "No results", "is_correct": False, "confidence": 0.0}
        
        # 计算加权投票
        total_weight = 0.0
        weighted_sum = 0.0
        
        for result in results:
            vote = result.get(self.vote_key, False)
            confidence = result.get(self.confidence_key, 0.5)
            
            total_weight += confidence
            if vote:
                weighted_sum += confidence
        
        # 加权平均
        weighted_average = weighted_sum / total_weight if total_weight > 0 else 0.0
        final_decision = weighted_average > 0.5
        
        # 找到代表性结果
        representative = max(results, key=lambda r: r.get(self.confidence_key, 0.0))
        
        # 添加投票信息
        representative = representative.copy()
        representative.update({
            self.vote_key: final_decision,
            "confidence": weighted_average,
            "voting_info": {
                "total_votes": len(results),
                "weighted_average": weighted_average,
                "total_weight": total_weight,
                "vote_method": "confidence_weighted"
            }
        })
        
        return representative


# ============================================================================
# Factory Functions
# ============================================================================

def create_math_pipeline(client, extract_boxed: bool = True, vote_method: str = "simple") -> JudgingPipeline:
    """Create a standard math judging pipeline."""
    
    prompt_builder = MathPromptBuilder()
    data_mapper = StandardDataMapper(extract_boxed=extract_boxed)
    response_parser = JsonResponseParser()
    
    if vote_method == "simple":
        vote_logic = SimpleVoteLogic()
    elif vote_method == "confidence":
        vote_logic = ConfidenceVoteLogic()
    else:
        raise ValueError(f"Unknown vote method: {vote_method}")
    
    return JudgingPipeline(
        prompt_builder=prompt_builder,
        data_mapper=data_mapper,
        response_parser=response_parser,
        vote_logic=vote_logic,
        client=client
    )

def create_custom_pipeline(client,
                          prompt_template: str,
                          data_mapping: Dict[str, str] = None,
                          vote_method: str = "simple",
                          extract_boxed: bool = False) -> JudgingPipeline:
    """Create a custom pipeline with user-defined components."""
    
    # Create prompt builder with custom template
    class CustomPromptBuilder(PromptBuilder):
        def build(self, data: DataTuple) -> str:
            return prompt_template.format(
                question=data.question,
                answer=data.answer,
                truth=data.truth,
                sample_id=data.sample_id,
                **data.metadata
            )
    
    # Create data mapper with custom key mapping
    mapping = data_mapping or {}
    data_mapper = StandardDataMapper(
        id_key=mapping.get("id", "id"),
        question_key=mapping.get("question", "input"),
        answer_key=mapping.get("answer", "output"),
        truth_key=mapping.get("truth", "gt"),
        extract_boxed=extract_boxed
    )
    
    response_parser = JsonResponseParser()
    
    if vote_method == "simple":
        vote_logic = SimpleVoteLogic()
    else:
        raise ValueError(f"Unknown vote method: {vote_method}")
    
    return JudgingPipeline(
        prompt_builder=CustomPromptBuilder(),
        data_mapper=data_mapper,
        response_parser=response_parser,
        vote_logic=vote_logic,
        client=client
    )
