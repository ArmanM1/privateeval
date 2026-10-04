from privateeval.eval.grounding import source_support
from privateeval.eval.privacy import canary_copy
from privateeval.eval.quality import HashingSemanticScorer, rouge_l, rouge_n


def test_rouge_exact_match():
    text = "The agency establishes a reserve."
    assert rouge_n(text, text, 1) == 1.0
    assert rouge_n(text, text, 2) == 1.0
    assert rouge_l(text, text) == 1.0


def test_metric_edges_are_safe():
    assert rouge_n("", "reference", 1) == 0.0
    assert rouge_l("", "") == 0.0
    assert HashingSemanticScorer().score_pairs([("", "")]) == [0.0]


def test_grounding_penalizes_unsupported_number():
    source = "The reserve contains no more than 40 million barrels."
    supported = source_support("The reserve is capped at 40 million barrels.", source)
    unsupported = source_support("The reserve is capped at 90 million barrels.", source)
    assert supported["source_support"] > unsupported["source_support"]


def test_privacy_normalization_detects_spaced_copy():
    result = canary_copy("Identifier: SYNTH SSN 900 88 7712", "SYNTH-SSN-900-88-7712")
    assert result == {"exact_copy": False, "normalized_copy": True}

