from app.services.chunking import split_into_chunks


def test_split_into_chunks_preserves_order_and_anchor():
    text = (
        "Jan 1, 2024 Initial intake note.\n\n"
        "Jan 5, 2024 Follow-up with more detail.\n\n"
        "Jan 10, 2024 Final review."
    )
    chunks = split_into_chunks(text, target_chars=60, overlap_chars=10)

    assert len(chunks) >= 2
    assert chunks[0].anchor_hint == "Jan 1, 2024"
    assert "Initial intake note." in chunks[0].content
    assert "Follow-up" in chunks[1].content

