"""Pure domain logic for Symposia.

This module contains only pure functions - no async, no network calls, no I/O.
These functions handle text parsing and calculations.
"""

import re
from typing import List, Dict
from collections import defaultdict
from .models import Stage2Result, AggregateRanking


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order (e.g., ["Response C", "Response A", "Response B"])
    """
    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Stage2Result],
    label_to_model: Dict[str, str]
) -> List[AggregateRanking]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of AggregateRanking objects, sorted best to worst (lowest average rank first)
    """
    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        parsed_ranking = ranking.parsed_ranking

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append(AggregateRanking(
                model=model,
                average_rank=round(avg_rank, 2),
                rankings_count=len(positions)
            ))

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x.average_rank)

    return aggregate
