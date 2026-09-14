"""Application boundary for recommendation construction."""

from analytics.recommendations import RecommendationInput, RecommendationResult, build_recommendation


def build_analysis_recommendation(inputs: RecommendationInput) -> RecommendationResult:
    """Delegate recommendation construction to the framework-independent core."""

    return build_recommendation(inputs)
