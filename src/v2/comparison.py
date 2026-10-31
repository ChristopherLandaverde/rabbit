"""Side-by-side comparison of attribution models (#17, SPEC_v2 section 7).

Each model's per-channel credits form a probability distribution over channels.
``model_agreement_score`` is 1 minus the mean pairwise Jensen-Shannon divergence
(JSD) of those distributions. JSD uses log base 2, so it lies in [0, 1] (Lin
1991) and the score does too: 1.0 means every model splits credit identically,
0.0 means every pair of models credits disjoint sets of channels.

The score measures how much the named rule-based models agree with each other on
this dataset. It says nothing about which model is right or about causal effect.

Definitional choices, with sources, are recorded in SPEC_v2 section 7:

- JSD(P, Q) = 0.5 * KL(P || M) + 0.5 * KL(Q || M), M = 0.5 * (P + Q), in bits.
  This is the divergence, not the Jensen-Shannon *distance* sqrt(JSD) that
  ``scipy.spatial.distance.jensenshannon`` returns.
- A channel a model gave no credit is a 0 entry in that model's distribution,
  and 0 * log(0) = 0 (Cover & Thomas). M is positive wherever P or Q is, so the
  divergence is always finite.
- Inputs are divided by their total before comparison, as scipy does, so float
  rounding in credits that should sum to 1 cannot push the result outside [0, 1].
"""

import math
from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

MODEL_AGREEMENT_METHOD = "jensen_shannon"


def _distribution(values: Mapping[str, float], keys: Sequence[str]) -> list[float]:
    for channel, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Credit for {channel!r} is not a number.")
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"Credit for {channel!r} must be finite and non-negative.")
    total = math.fsum(values.values())
    if total <= 0:
        raise ValueError("A distribution needs positive total credit.")
    return [values.get(key, 0.0) / total for key in keys]


def jensen_shannon_divergence(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    """JSD of two channel-credit distributions, in bits (log base 2), in [0, 1].

    Channels absent from one mapping count as 0 credit there.
    """
    keys = sorted(set(p) | set(q))
    p_values, q_values = _distribution(p, keys), _distribution(q, keys)
    terms = []
    for a, b in zip(p_values, q_values):
        # a * log2(a / m) with m = (a + b) / 2, written as 2a / (a + b) so the
        # ratio stays exact for tiny a; 0 * log(0 / m) = 0 terms are skipped.
        if a > 0:
            terms.append(0.5 * a * math.log2(2 * a / (a + b)))
        if b > 0:
            terms.append(0.5 * b * math.log2(2 * b / (a + b)))
    return min(1.0, max(0.0, math.fsum(terms)))


def model_agreement_score(distributions: Sequence[Mapping[str, float]]) -> float | None:
    """1 - mean pairwise JSD over all N(N-1)/2 pairs; None for fewer than 2 models."""
    pairs = list(combinations(distributions, 2))
    if not pairs:
        return None
    mean = math.fsum(jensen_shannon_divergence(p, q) for p, q in pairs) / len(pairs)
    return min(1.0, max(0.0, 1.0 - mean))


def build_comparison(models: Sequence[str], results: Mapping[str, Any]) -> dict | None:
    """Thin comparison block: channel keys and per-model credit, nothing else (C4).

    Conversions, revenue and parameters stay in ``results``. Returns None for a
    single-model analysis, which has no pair of models to compare.
    """
    if len(models) < 2:
        return None
    credits = {
        model: {
            channel: float(values["credit"])
            for channel, values in (results[model].get("channels") or {}).items()
        }
        for model in models
    }
    channels = sorted(set().union(*(set(c) for c in credits.values())))
    block = {}
    for channel in channels:
        by_model = {model: credits[model].get(channel, 0.0) for model in models}
        # max/min return the first extreme in request order, so ties are stable.
        most = max(models, key=lambda model: by_model[model])
        least = min(models, key=lambda model: by_model[model])
        block[channel] = {
            "credit_by_model": by_model,
            "credit_spread": by_model[most] - by_model[least],
            "most_favorable_model": most,
            "least_favorable_model": least,
        }
    has_mass = all(math.fsum(c.values()) > 0 for c in credits.values())
    score = model_agreement_score([credits[m] for m in models]) if has_mass else None
    return {
        "channels": block,
        "model_agreement_score": score,
        "model_agreement_method": MODEL_AGREEMENT_METHOD,
    }
