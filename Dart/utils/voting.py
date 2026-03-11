"""
Enhanced voting system with separated vote aggregation and result computation.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional, Union
from dataclasses import dataclass

class VoteAggregator(ABC):
    """Abstract base class for aggregating votes from multiple results."""
    
    @abstractmethod
    def aggregate(self, results: List[Dict[str, Any]], vote_key: str = "is_correct") -> Dict[str, Any]:
        """
        Aggregate multiple results into voting statistics.
        
        Args:
            results: List of judgment results
            vote_key: Key to extract votes from
            
        Returns:
            Dictionary containing aggregated voting information
        """
        pass

class ResultComputer(ABC):
    """Abstract base class for computing final results from aggregated votes."""
    
    @abstractmethod
    def compute(self, vote_stats: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute final result from voting statistics.
        
        Args:
            vote_stats: Aggregated voting statistics
            results: Original list of results
            
        Returns:
            Final computed result
        """
        pass

@dataclass
class VotingConfig:
    """Configuration for voting behavior."""
    vote_key: str = "is_correct"
    aggregator: Optional[VoteAggregator] = None
    computer: Optional[ResultComputer] = None
    metadata_fields: List[str] = None  # Fields to include in voting metadata
    
    def __post_init__(self):
        if self.metadata_fields is None:
            self.metadata_fields = ["confidence", "reasoning"]

class EnhancedVotingStrategy:
    """Enhanced voting strategy that separates aggregation and computation."""
    
    def __init__(self, config: VotingConfig):
        self.config = config
    
    def vote(self, results: List[Dict[str, Any]], vote_key: str = None) -> Dict[str, Any]:
        """Apply voting using configured aggregator and computer."""
        if not results:
            return self._get_empty_result()
        
        vote_key = vote_key or self.config.vote_key
        
        # Step 1: Aggregate votes
        vote_stats = self.config.aggregator.aggregate(results, vote_key)
        
        # Step 2: Compute final result
        final_result = self.config.computer.compute(vote_stats, results)
        
        return final_result
    
    def _get_empty_result(self) -> Dict[str, Any]:
        """Return default result when no results are available."""
        return {
            "reasoning": "No results to vote on",
            "is_correct": False,
            "confidence": 0.0,
            "voting_info": {
                "total_votes": 0,
                "vote_method": "empty"
            }
        }

# ============================================================================
# Vote Aggregators
# ============================================================================

class SimpleVoteAggregator(VoteAggregator):
    """Simple aggregator that counts votes."""
    
    def aggregate(self, results: List[Dict[str, Any]], vote_key: str = "is_correct") -> Dict[str, Any]:
        votes = [result.get(vote_key, False) for result in results]
        positive_votes = votes.count(True)
        total_votes = len(votes)
        
        return {
            "votes": votes,
            "positive_votes": positive_votes,
            "total_votes": total_votes,
            "positive_ratio": positive_votes / total_votes if total_votes > 0 else 0.0,
            "unanimous": len(set(votes)) == 1,
            "aggregation_method": "simple"
        }

class WeightedVoteAggregator(VoteAggregator):
    """Aggregator that weights votes by confidence."""
    
    def __init__(self, weight_key: str = "confidence"):
        self.weight_key = weight_key
    
    def aggregate(self, results: List[Dict[str, Any]], vote_key: str = "is_correct") -> Dict[str, Any]:
        votes = []
        weights = []
        weighted_score = 0.0
        total_weight = 0.0
        
        for result in results:
            vote = result.get(vote_key, False)
            weight = result.get(self.weight_key, 0.5)
            
            votes.append(vote)
            weights.append(weight)
            
            weighted_score += weight * (1.0 if vote else 0.0)
            total_weight += weight
        
        return {
            "votes": votes,
            "weights": weights,
            "weighted_score": weighted_score,
            "total_weight": total_weight,
            "normalized_score": weighted_score / total_weight if total_weight > 0 else 0.0,
            "positive_votes": votes.count(True),
            "total_votes": len(votes),
            "aggregation_method": "weighted"
        }

class ConfidenceDistributionAggregator(VoteAggregator):
    """Aggregator that analyzes confidence distribution."""
    
    def aggregate(self, results: List[Dict[str, Any]], vote_key: str = "is_correct") -> Dict[str, Any]:
        votes = [result.get(vote_key, False) for result in results]
        confidences = [result.get("confidence", 0.5) for result in results]
        
        positive_confidences = [conf for vote, conf in zip(votes, confidences) if vote]
        negative_confidences = [conf for vote, conf in zip(votes, confidences) if not vote]
        
        positive_votes = votes.count(True)
        total_votes = len(votes)
        
        return {
            "votes": votes,
            "confidences": confidences,
            "positive_votes": positive_votes,
            "total_votes": total_votes,
            "positive_ratio": positive_votes / total_votes if total_votes > 0 else 0.0,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            "avg_positive_confidence": sum(positive_confidences) / len(positive_confidences) if positive_confidences else 0.0,
            "avg_negative_confidence": sum(negative_confidences) / len(negative_confidences) if negative_confidences else 0.0,
            "confidence_variance": self._calculate_variance(confidences),
            "unanimous": len(set(votes)) == 1,
            "aggregation_method": "confidence_distribution"
        }
    
    def _calculate_variance(self, values: List[float]) -> float:
        if len(values) <= 1:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)

# ============================================================================
# Result Computers
# ============================================================================

class MajorityResultComputer(ResultComputer):
    """Computer that uses simple majority rule."""
    
    def compute(self, vote_stats: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
        positive_votes = vote_stats["positive_votes"]
        total_votes = vote_stats["total_votes"]
        
        majority_decision = positive_votes > total_votes // 2
        
        # Find representative result
        representative = self._find_representative(results, majority_decision)
        
        # Add voting metadata
        representative = representative.copy()
        representative.update({
            vote_stats.get("vote_key", "is_correct"): majority_decision,
            "voting_info": {
                **vote_stats,
                "final_decision": majority_decision,
                "decision_method": "majority",
                "decision_margin": abs(positive_votes - (total_votes - positive_votes))
            }
        })
        
        return representative
    
    def _find_representative(self, results: List[Dict[str, Any]], target_vote: bool) -> Dict[str, Any]:
        """Find a representative result that matches the target vote."""
        for result in results:
            if result.get("is_correct", False) == target_vote:
                return result
        return results[0] if results else {}

class ThresholdResultComputer(ResultComputer):
    """Computer that uses threshold-based decision."""
    
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
    
    def compute(self, vote_stats: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
        positive_ratio = vote_stats["positive_ratio"]
        threshold_decision = positive_ratio >= self.threshold
        
        representative = self._find_representative(results, threshold_decision)
        
        representative = representative.copy()
        representative.update({
            vote_stats.get("vote_key", "is_correct"): threshold_decision,
            "voting_info": {
                **vote_stats,
                "final_decision": threshold_decision,
                "decision_method": "threshold",
                "threshold": self.threshold,
                "threshold_margin": positive_ratio - self.threshold
            }
        })
        
        return representative
    
    def _find_representative(self, results: List[Dict[str, Any]], target_vote: bool) -> Dict[str, Any]:
        for result in results:
            if result.get("is_correct", False) == target_vote:
                return result
        return results[0] if results else {}

class WeightedResultComputer(ResultComputer):
    """Computer that uses weighted average for decision."""
    
    def __init__(self, decision_threshold: float = 0.5):
        self.decision_threshold = decision_threshold
    
    def compute(self, vote_stats: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
        normalized_score = vote_stats["normalized_score"]
        weighted_decision = normalized_score > self.decision_threshold
        
        # Find result with highest confidence as representative
        representative = max(results, key=lambda r: r.get("confidence", 0.0))
        
        representative = representative.copy()
        representative.update({
            vote_stats.get("vote_key", "is_correct"): weighted_decision,
            "confidence": normalized_score if weighted_decision else 1.0 - normalized_score,
            "voting_info": {
                **vote_stats,
                "final_decision": weighted_decision,
                "decision_method": "weighted",
                "decision_threshold": self.decision_threshold,
                "final_confidence": normalized_score
            }
        })
        
        return representative

class EnsembleResultComputer(ResultComputer):
    """Computer that combines multiple decision criteria."""
    
    def __init__(self, majority_weight: float = 0.4, confidence_weight: float = 0.4, 
                 consensus_weight: float = 0.2):
        self.majority_weight = majority_weight
        self.confidence_weight = confidence_weight
        self.consensus_weight = consensus_weight
    
    def compute(self, vote_stats: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Majority component
        positive_ratio = vote_stats["positive_ratio"]
        majority_score = positive_ratio
        
        # Confidence component
        avg_confidence = vote_stats.get("avg_confidence", 0.5)
        confidence_score = avg_confidence
        
        # Consensus component (higher if votes are unanimous)
        consensus_score = 1.0 if vote_stats.get("unanimous", False) else positive_ratio
        
        # Combined score
        ensemble_score = (
            self.majority_weight * majority_score +
            self.confidence_weight * confidence_score +
            self.consensus_weight * consensus_score
        )
        
        ensemble_decision = ensemble_score > 0.5
        
        # Find best representative
        representative = max(results, key=lambda r: r.get("confidence", 0.0))
        
        representative = representative.copy()
        representative.update({
            vote_stats.get("vote_key", "is_correct"): ensemble_decision,
            "confidence": ensemble_score,
            "voting_info": {
                **vote_stats,
                "final_decision": ensemble_decision,
                "decision_method": "ensemble",
                "ensemble_score": ensemble_score,
                "majority_score": majority_score,
                "confidence_score": confidence_score,
                "consensus_score": consensus_score,
                "weights": {
                    "majority": self.majority_weight,
                    "confidence": self.confidence_weight,
                    "consensus": self.consensus_weight
                }
            }
        })
        
        return representative

# ============================================================================
# Factory Functions
# ============================================================================

def create_voting_strategy(strategy_type: str, **kwargs) -> EnhancedVotingStrategy:
    """Factory function to create voting strategies."""
    
    if strategy_type == "majority":
        config = VotingConfig(
            aggregator=SimpleVoteAggregator(),
            computer=MajorityResultComputer()
        )
    
    elif strategy_type == "threshold":
        threshold = kwargs.get("threshold", 0.6)
        config = VotingConfig(
            aggregator=SimpleVoteAggregator(),
            computer=ThresholdResultComputer(threshold=threshold)
        )
    
    elif strategy_type == "weighted":
        weight_key = kwargs.get("weight_key", "confidence")
        decision_threshold = kwargs.get("decision_threshold", 0.5)
        config = VotingConfig(
            aggregator=WeightedVoteAggregator(weight_key=weight_key),
            computer=WeightedResultComputer(decision_threshold=decision_threshold)
        )
    
    elif strategy_type == "ensemble":
        config = VotingConfig(
            aggregator=ConfidenceDistributionAggregator(),
            computer=EnsembleResultComputer(
                majority_weight=kwargs.get("majority_weight", 0.4),
                confidence_weight=kwargs.get("confidence_weight", 0.4),
                consensus_weight=kwargs.get("consensus_weight", 0.2)
            )
        )
    
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    return EnhancedVotingStrategy(config)
