from dataclasses import dataclass

MERGE_THRESHOLD = 100  # paragraphs under this word count get merged


@dataclass
class Chunk:
    text: str
    index: int


class TextChunker:
    """Hybrid text chunker: split by paragraphs, merge small, split large."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, text: str) -> list[Chunk]:
        if not text or not text.strip():
            return []

        # Step 1: Split by paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        # Step 2: Merge small paragraphs
        merged = self._merge_small(paragraphs)

        # Step 3: Split large blocks
        raw_chunks = []
        for block in merged:
            if self._word_count(block) > self.max_tokens:
                raw_chunks.extend(self._split_large(block))
            else:
                raw_chunks.append(block)

        return [Chunk(text=t, index=i) for i, t in enumerate(raw_chunks)]

    def _word_count(self, text: str) -> int:
        return len(text.split())

    def _merge_small(self, paragraphs: list[str]) -> list[str]:
        if not paragraphs:
            return []

        merged = []
        current = paragraphs[0]

        for para in paragraphs[1:]:
            combined_count = self._word_count(current) + self._word_count(para)
            if self._word_count(current) < MERGE_THRESHOLD and combined_count <= self.max_tokens:
                current = current + "\n\n" + para
            else:
                merged.append(current)
                current = para

        merged.append(current)
        return merged

    def _split_large(self, text: str) -> list[str]:
        """Split a large block by sentences, with overlap."""
        # Split on ". " (sentence boundary) while preserving the period
        parts = text.split(". ")
        sentences = [p + "." for p in parts[:-1]] + [parts[-1]] if len(parts) > 1 else [text]
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current_words = []
        current_count = 0

        for sentence in sentences:
            words = sentence.split()
            if current_count + len(words) > self.max_tokens and current_words:
                chunks.append(" ".join(current_words))
                # Keep overlap
                overlap_words = current_words[-self.overlap_tokens:] if self.overlap_tokens else []
                current_words = overlap_words
                current_count = len(current_words)
            current_words.extend(words)
            current_count += len(words)

        if current_words:
            chunks.append(" ".join(current_words))

        return chunks if chunks else [text]
