from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    location: str | None = None


class DocumentChunker:
    def __init__(self, chunk_size: int, overlap: int) -> None:
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[TextChunk]:
        paragraphs = [part.strip() for part in text.replace("\r\n", "\n").split("\n") if part.strip()]
        chunks: list[TextChunk] = []
        buffer = ""
        location: str | None = None
        buffer_location: str | None = None
        for paragraph in paragraphs:
            if paragraph.startswith(("Sayfa: ", "Slayt: ", "Page: ")):
                if buffer:
                    chunks.append(TextChunk(len(chunks), buffer, buffer_location))
                    buffer = buffer[-self.overlap :].strip() if self.overlap else ""
                location = paragraph
                buffer_location = location
                continue
            candidate = f"{buffer}\n{paragraph}".strip()
            if buffer and len(candidate) > self.chunk_size:
                chunks.append(TextChunk(len(chunks), buffer, buffer_location))
                tail = buffer[-self.overlap :] if self.overlap else ""
                buffer = f"{tail}\n{paragraph}".strip()
                buffer_location = location
            else:
                buffer = candidate
                buffer_location = buffer_location or location
            while len(buffer) > self.chunk_size:
                chunks.append(TextChunk(len(chunks), buffer[: self.chunk_size].strip(), buffer_location))
                start = self.chunk_size - self.overlap
                buffer = buffer[start:].strip()
        if buffer:
            chunks.append(TextChunk(len(chunks), buffer, buffer_location))
        return chunks
