"""Jensen-Shannon comparison math for multi-model analyses (#17, SPEC_v2 section 7).

The golden file holds cases worked by hand before the implementation existed.
The randomized checks use a fixed seed so a failure always reproduces.
"""

import json
import math
import random
from pathlib import Path

import pytest

from src.v2.comparison import (
    MODEL_AGREEMENT_METHOD,
    build_comparison,
    jensen_shannon_divergence,
    model_agreement_score,
)

GOLDEN = json.loads((Path(__file__).parent / "golden" / "jsd_golden.json").read_text())
TOLERANCE = 1e-12


@pytest.mark.parametrize("case", GOLDEN["jsd_cases"], ids=lambda case: case["name"])
def test_jsd_matches_hand_computed_golden_values(case):
    assert jensen_shannon_divergence(case["p"], case["q"]) == pytest.approx(
        case["jsd"], abs=TOLERANCE
    )
    # JSD is symmetric.
    assert jensen_shannon_divergence(case["q"], case["p"]) == pytest.approx(
        case["jsd"], abs=TOLERANCE
    )


def test_identical_distributions_give_exactly_zero():
    p = {"email": 0.1, "social": 0.2, "organic": 0.7}
    assert jensen_shannon_divergence(p, dict(p)) == 0.0


@pytest.mark.parametrize("case", GOLDEN["agreement_cases"], ids=lambda case: case["name"])
def test_agreement_matches_hand_computed_golden_values(case):
    assert model_agreement_score(case["distributions"]) == pytest.approx(
        case["model_agreement_score"], abs=TOLERANCE
    )
    assert 1.0 - case["mean_pairwise_jsd"] == pytest.approx(
        case["model_agreement_score"], abs=TOLERANCE
    )


def test_agreement_is_undefined_for_fewer_than_two_models():
    assert model_agreement_score([]) is None
    assert model_agreement_score([{"email": 1.0}]) is None


@pytest.mark.parametrize(
    "p,q",
    [
        ({"email": -0.1, "social": 1.1}, {"email": 1.0}),
        ({"email": float("nan")}, {"email": 1.0}),
        ({"email": float("inf")}, {"email": 1.0}),
        ({"email": 0.0}, {"email": 1.0}),
        ({}, {"email": 1.0}),
    ],
    ids=["negative", "nan", "inf", "all_zero", "empty"],
)
def test_jsd_rejects_inputs_that_are_not_distributions(p, q):
    with pytest.raises(ValueError):
        jensen_shannon_divergence(p, q)
    with pytest.raises(ValueError):
        jensen_shannon_divergence(q, p)


def _random_distribution(rng, channels):
    """A random credit vector over a random subset of channels, zeros included."""
    chosen = rng.sample(channels, rng.randint(1, len(channels)))
    style = rng.random()
    values = {}
    for channel in chosen:
        if style < 0.2:
            values[channel] = rng.choice([0.0, 1.0, 1e-300, 1e-12, 1e6])
        elif style < 0.4:
            values[channel] = rng.random() ** 8  # very skewed, many near-zero values
        else:
            values[channel] = rng.random()
    if sum(values.values()) <= 0:
        values[chosen[0]] = 1.0
    return values


def test_property_jsd_is_bounded_symmetric_and_zero_on_self():
    """For any valid pair of distributions, 0 <= JSD <= 1 with log base 2."""
    rng = random.Random(17)
    channels = [f"channel_{i}" for i in range(12)]
    for _ in range(5000):
        p = _random_distribution(rng, channels)
        q = _random_distribution(rng, channels)
        value = jensen_shannon_divergence(p, q)
        assert 0.0 <= value <= 1.0, (p, q, value)
        assert value == pytest.approx(jensen_shannon_divergence(q, p), abs=TOLERANCE)
        assert jensen_shannon_divergence(p, p) == pytest.approx(0.0, abs=TOLERANCE)


def test_property_agreement_is_bounded():
    rng = random.Random(1717)
    channels = [f"channel_{i}" for i in range(8)]
    for _ in range(1000):
        distributions = [_random_distribution(rng, channels) for _ in range(rng.randint(2, 5))]
        score = model_agreement_score(distributions)
        assert 0.0 <= score <= 1.0, (distributions, score)


def test_jsd_agrees_with_scipy_squared_distance():
    """Independent cross-check: scipy returns the JS *distance*, sqrt(JSD)."""
    distance = pytest.importorskip("scipy.spatial.distance")
    rng = random.Random(2026)
    channels = [f"channel_{i}" for i in range(6)]
    for _ in range(500):
        p = _random_distribution(rng, channels)
        q = _random_distribution(rng, channels)
        keys = sorted(set(p) | set(q))
        expected = distance.jensenshannon(
            [p.get(k, 0.0) for k in keys], [q.get(k, 0.0) for k in keys], base=2
        ) ** 2
        assert jensen_shannon_divergence(p, q) == pytest.approx(expected, abs=1e-9)


def _results(**credits_by_model):
    return {
        model: {"model": model, "channels": {
            channel: {"credit": credit, "conversions": 1, "revenue": 10.0}
            for channel, credit in credits.items()
        }}
        for model, credits in credits_by_model.items()
    }


def test_comparison_block_is_thin_and_fills_missing_channels_with_zero():
    models = ["first_touch", "last_touch", "linear"]
    results = _results(
        first_touch={"email": 0.5, "social": 0.5},
        last_touch={"email": 1.0},
        linear={"email": 0.5, "social": 0.25, "organic": 0.25},
    )
    comparison = build_comparison(models, results)

    assert comparison["model_agreement_method"] == MODEL_AGREEMENT_METHOD == "jensen_shannon"
    assert set(comparison["channels"]) == {"email", "social", "organic"}
    for entry in comparison["channels"].values():
        assert set(entry) == {
            "credit_by_model", "credit_spread", "most_favorable_model", "least_favorable_model",
        }
        assert list(entry["credit_by_model"]) == models

    social = comparison["channels"]["social"]
    assert social["credit_by_model"] == {"first_touch": 0.5, "last_touch": 0.0, "linear": 0.25}
    assert social["credit_spread"] == 0.5
    assert social["most_favorable_model"] == "first_touch"
    assert social["least_favorable_model"] == "last_touch"

    expected = 1.0 - (
        jensen_shannon_divergence({"email": 0.5, "social": 0.5}, {"email": 1.0})
        + jensen_shannon_divergence(
            {"email": 0.5, "social": 0.5}, {"email": 0.5, "social": 0.25, "organic": 0.25}
        )
        + jensen_shannon_divergence({"email": 1.0}, {"email": 0.5, "social": 0.25, "organic": 0.25})
    ) / 3
    assert comparison["model_agreement_score"] == pytest.approx(expected, abs=TOLERANCE)


def test_comparison_ties_resolve_to_request_order():
    comparison = build_comparison(
        ["linear", "time_decay"],
        _results(linear={"email": 0.5, "social": 0.5}, time_decay={"email": 0.5, "social": 0.5}),
    )
    email = comparison["channels"]["email"]
    assert email["credit_spread"] == 0.0
    assert email["most_favorable_model"] == "linear"
    assert email["least_favorable_model"] == "linear"
    assert comparison["model_agreement_score"] == 1.0


def test_no_comparison_for_a_single_model():
    assert build_comparison(["linear"], _results(linear={"email": 1.0})) is None


def test_comparison_without_conversions_has_no_channels_and_no_score():
    comparison = build_comparison(["linear", "first_touch"], _results(linear={}, first_touch={}))
    assert comparison == {
        "channels": {},
        "model_agreement_score": None,
        "model_agreement_method": "jensen_shannon",
    }


def test_agreement_score_is_finite_on_rounding_noise():
    # Credits that sum to 1 only up to float error must still give a valid score.
    third = 1 / 3
    comparison = build_comparison(
        ["linear", "first_touch"],
        _results(linear={"a": third, "b": third, "c": third}, first_touch={"a": 0.1 + 0.2, "b": 0.7}),
    )
    assert math.isfinite(comparison["model_agreement_score"])
    assert 0.0 <= comparison["model_agreement_score"] <= 1.0
