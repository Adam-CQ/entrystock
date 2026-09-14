from analytics.scoring import (
    SUPPORTED_COMPONENTS,
    ScoreConfiguration,
    ScoreNormalization,
    calculate_composite_score,
    validate_score_configuration,
)


def _values(value=0.5):
    return {component: value for component in SUPPORTED_COMPONENTS}


def test_default_composite_score_is_versioned_deterministic_and_inspectable():
    result = calculate_composite_score(_values())

    assert result.valid
    assert result.aggregate_score == 0.5
    assert result.configuration_version == "v1"
    assert result.preset == "balanced"
    assert [item.component for item in result.contributions] == list(SUPPORTED_COMPONENTS)
    assert all(item.normalized_value == 0.5 and item.status == "ok" for item in result.contributions)
    assert result.coverage == 1
    assert result.confidence == "high"


def test_custom_weights_and_normalization_are_applied_and_reported():
    config = ScoreConfiguration(
        version="v2",
        preset="quality-first",
        weights={component: (1 if component == "quality" else 0) for component in SUPPORTED_COMPONENTS},
        normalizations={"quality": ScoreNormalization(0, 100)},
    )
    result = calculate_composite_score({"quality": 75}, config)

    quality = next(item for item in result.contributions if item.component == "quality")
    assert result.aggregate_score == 0.75
    assert quality.normalized_value == 0.75
    assert quality.contribution == 0.75
    assert result.configuration_version == "v2"
    assert result.preset == "quality-first"


def test_missing_components_reduce_coverage_and_confidence_without_becoming_zero_scores():
    result = calculate_composite_score({"valuation": 1.0})

    assert result.aggregate_score == 1.0
    assert result.coverage == 0.25
    assert result.confidence == "reduced"
    missing = next(item for item in result.contributions if item.component == "momentum")
    assert missing.value is None
    assert missing.contribution == 0
    assert missing.status == "not_evaluable"
    assert "missing components reduce coverage" in result.explanation


def test_invalid_weights_ranges_and_component_names_return_structured_errors():
    config = ScoreConfiguration(weights={"valuation": -1}, normalizations={"unknown": ScoreNormalization()})
    result = calculate_composite_score({"valuation": 0.5, "unknown": 0.5}, config)

    assert not result.valid
    assert any("missing components" in error for error in result.errors)
    assert any("unsupported normalization" in error for error in result.errors)
    assert any("unsupported component values" in error for error in result.errors)
    assert any("non-negative" in error for error in result.errors)


def test_normalization_boundaries_and_inversion_are_deterministic():
    config = ScoreConfiguration(normalizations={"risk": ScoreNormalization(0, 10, invert=True)})
    low = calculate_composite_score({"risk": 0}, config)
    high = calculate_composite_score({"risk": 10}, config)

    assert next(item for item in low.contributions if item.component == "risk").normalized_value == 1
    assert next(item for item in high.contributions if item.component == "risk").normalized_value == 0
    assert validate_score_configuration(config) == ()
