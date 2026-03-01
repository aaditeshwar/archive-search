"""Text chunking for indexing."""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_text_splitter(
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    separators: list[str] | None = None,
) -> RecursiveCharacterTextSplitter:
    """Return a configured RecursiveCharacterTextSplitter."""
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        length_function=len,
    )


def chunk_text(text: str, **kwargs) -> list[str]:
    """Split text into chunks. Returns list of chunk strings."""
    splitter = get_text_splitter(**kwargs)
    return splitter.split_text(text)
