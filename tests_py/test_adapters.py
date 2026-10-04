from privateeval.models.extractive import ExtractiveAdapter, MockOpenConfigAdapter


def test_extractive_contract_handles_empty_and_oversized_input():
    adapter = ExtractiveAdapter(
        {"id": "lead-3", "label": "Lead-3", "kind": "extractive", "max_sentences": 3}
    )
    adapter.load()
    assert adapter.summarize("").text == ""
    output = adapter.summarize("Sentence one. " * 1000)
    assert len(output.text.split()) <= 90
    assert output.metadata["algorithm"]


def test_mock_adapter_cannot_hide_simulation_provenance():
    adapter = MockOpenConfigAdapter(
        {"id": "mock-int8", "label": "Mock", "kind": "mock-open-config", "max_sentences": 2}
    )
    adapter.load()
    result = adapter.summarize("A public source states the main action. A condition follows.")
    assert result.metadata["simulated"] is True

