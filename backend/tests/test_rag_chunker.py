from app.rag.chunker import TextChunker, Chunk


def test_chunk_dataclass():
    c = Chunk(text="hello", index=0)
    assert c.text == "hello"
    assert c.index == 0


def test_single_short_paragraph():
    chunker = TextChunker(max_tokens=500, overlap_tokens=50)
    result = chunker.chunk("This is a short paragraph.")
    assert len(result) == 1
    assert result[0].text == "This is a short paragraph."
    assert result[0].index == 0


def test_multiple_paragraphs_under_limit():
    chunker = TextChunker(max_tokens=500, overlap_tokens=50)
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    result = chunker.chunk(text)
    # Each paragraph is short, but merge-small should combine them
    # Total ~6 words, well under 500
    assert len(result) == 1


def test_merge_small_paragraphs():
    chunker = TextChunker(max_tokens=20, overlap_tokens=5)
    text = "One.\n\nTwo.\n\nThree."
    result = chunker.chunk(text)
    # All are tiny, should merge into one chunk (3 words total < 20)
    assert len(result) == 1
    assert "One." in result[0].text
    assert "Three." in result[0].text


def test_split_large_paragraph():
    chunker = TextChunker(max_tokens=10, overlap_tokens=2)
    # Create a paragraph with ~20 words (no \n\n so it's one paragraph)
    words = ["word"] * 20
    text = " ".join(words)
    result = chunker.chunk(text)
    assert len(result) >= 2
    # Each chunk should be roughly max_tokens or less
    for chunk in result:
        word_count = len(chunk.text.split())
        assert word_count <= 12  # max_tokens + some tolerance for overlap


def test_mixed_paragraphs():
    chunker = TextChunker(max_tokens=10, overlap_tokens=2)
    short = "Short."
    long = " ".join(["word"] * 20)
    text = f"{short}\n\n{long}"
    result = chunker.chunk(text)
    # Short paragraph + long paragraph that gets split
    assert len(result) >= 2


def test_empty_text():
    chunker = TextChunker(max_tokens=500, overlap_tokens=50)
    result = chunker.chunk("")
    assert result == []


def test_chunk_indices_sequential():
    chunker = TextChunker(max_tokens=10, overlap_tokens=2)
    text = " ".join(["word"] * 30)
    result = chunker.chunk(text)
    for i, chunk in enumerate(result):
        assert chunk.index == i
