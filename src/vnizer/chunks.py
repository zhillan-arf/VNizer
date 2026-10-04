"""Split narration at sentence, clause, or word boundaries."""

import re

ABBREVIATIONS = {"dr", "mr", "mrs", "ms", "prof", "fig", "eq", "e.g", "i.e", "vs", "etc"}


def sentences(text):
    start = 0
    for match in re.finditer(r'[.!?。！？]+[”’"\')\]]*(?:\s+|$)|[。！？]+', text):
        end = match.end()
        token = text[start:match.start()].split()
        previous = token[-1].lower() if token else ""
        if match.group().startswith(".") and (
            previous in ABBREVIATIONS or (len(previous) == 1 and previous.isalpha())
        ):
            continue
        yield text[start:end].strip()
        start = end
    if text[start:].strip():
        yield text[start:].strip()


def chunk_text(text, limit=512):
    if limit < 1:
        raise ValueError("The chunk limit must be positive.")
    text = re.sub(r"\s+", " ", text).strip()
    result = []
    current = ""
    for sentence in sentences(text):
        if current and len(current) + 1 + len(sentence) <= limit:
            current += " " + sentence
            continue
        if current:
            result.append(current)
            current = ""
        while len(sentence) > limit:
            window = sentence[:limit]
            commas = [m.end() for m in re.finditer(r"[,，;；:]", window)]
            split = commas[-1] if commas else window.rfind(" ")
            if split <= 0:
                split = limit
            result.append(sentence[:split].strip())
            sentence = sentence[split:].strip()
        current = sentence
    if current:
        result.append(current)
    return result
