from privateeval.data.perturb import apply_perturbation


SOURCE = "The Secretary establishes a regional reserve with strict security requirements."


def test_perturbations_are_deterministic_and_nonempty():
    for name in ("typos", "formatting", "length_shift"):
        first = apply_perturbation(name, SOURCE, 17)
        second = apply_perturbation(name, SOURCE, 17)
        assert first == second
        assert first
        assert first != SOURCE

