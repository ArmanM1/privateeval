from privateeval.analysis.stats import bootstrap_mean_ci, paired_bootstrap_difference


def test_bootstrap_is_deterministic():
    first = bootstrap_mean_ci([0.1, 0.2, 0.3], 500, 0.95, 7)
    second = bootstrap_mean_ci([0.1, 0.2, 0.3], 500, 0.95, 7)
    assert first == second


def test_known_paired_difference_and_effect_direction():
    result = paired_bootstrap_difference(
        [0.8, 0.7, 0.9, 0.6], [0.6, 0.5, 0.7, 0.4], 1000, 0.95, 11
    )
    assert result["difference"] == 0.2
    assert result["low"] > 0
    assert result["common_language_probability"] == 1.0

