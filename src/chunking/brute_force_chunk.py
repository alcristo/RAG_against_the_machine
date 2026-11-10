def recursive_text_split(text: str, max_size: int = 2000) -> list[str]:
    if len(text) <= max_size:
        return [text.strip()]

    separators = ["\n\n", "\n", ". ", " "]

    for sep in separators:
        parts = text.split(sep)
        if len(parts) == 1:
            continue

        chunks: list[str] = []
        current = ""

        for part in parts:
            candidate = f"{current}{sep}{part}" if current else part

            if len(candidate) <= max_size:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())
                if len(part) > max_size:
                    chunks.extend(recursive_text_split(part, max_size))
                else:
                    current = part
                    continue

                current = ""

        if current:
            chunks.append(current.strip())
        return [chunk for chunk in chunks if chunk]

    return [
        text[i:i + max_size]
        for i in range(0, len(text), max_size)
    ]


def recursive_py_split(text: str, max_size: int = 2000) -> list[str]:
    if len(text) <= max_size:
        return [text.strip()]

    separators = ["\n\n\n", "\n\n", "\n", ". ", " "]

    for sep in separators:
        parts = text.split(sep)
        if len(parts) == 1:
            continue

        chunks: list[str] = []
        current = ""

        for part in parts:
            candidate = f"{current}{sep}{part}" if current else part

            if len(candidate) <= max_size:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())
                if len(part) > max_size:
                    chunks.extend(recursive_text_split(part, max_size))
                else:
                    current = part
                    continue

                current = ""

        if current:
            chunks.append(current.strip())
        return [chunk for chunk in chunks if chunk]

    return [
        text[i:i + max_size]
        for i in range(0, len(text), max_size)
    ]
