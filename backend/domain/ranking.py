"""Ranking parsing and aggregation helpers (domain logic)."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def parse_ranking_from_text(ranking_text: str) -> list[str]:
    """Extract a ranked list of 'Response X' labels from a model evaluation."""
    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:", 1)
        ranking_section = parts[1] if len(parts) > 1 else ""

        numbered_matches = re.findall(r"\d+\.\s*Response [A-Z]", ranking_section)
        if numbered_matches:
            return [re.search(r"Response [A-Z]", m).group() for m in numbered_matches]  # type: ignore[union-attr]

        return re.findall(r"Response [A-Z]", ranking_section)

    return re.findall(r"Response [A-Z]", ranking_text)


def calculate_aggregate_rankings(
    stage2_results: list[dict[str, Any]],
    label_to_model: dict[str, str],
) -> list[dict[str, Any]]:
    """Compute average rank per model across peer evaluations."""
    model_positions: dict[str, list[int]] = defaultdict(list)

    for ranking in stage2_results:
        parsed_ranking = ranking.get("parsed_ranking") or parse_ranking_from_text(
            ranking.get("ranking", "")
        )
        for position, label in enumerate(parsed_ranking, start=1):
            model_name = label_to_model.get(label)
            if model_name:
                model_positions[model_name].append(position)

    aggregate: list[dict[str, Any]] = []
    for model, positions in model_positions.items():
        if not positions:
            continue
        avg_rank = sum(positions) / len(positions)
        aggregate.append(
            {
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions),
            }
        )

    aggregate.sort(key=lambda x: x["average_rank"])
    return aggregate

