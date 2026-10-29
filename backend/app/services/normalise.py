import re

HONORIFICS = r"\b(sri|smt|shri|mr|mrs|ms|dr|late|s/o|w/o|d/o)\b\.?"


def norm_name(s: str) -> str:
    """Lowercase, drop honorifics/punctuation, collapse spaces. Original is stored separately."""
    s = re.sub(HONORIFICS, " ", s.lower())
    s = re.sub(r"[^a-z0-9ఀ-౿ ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_value(type_: str, s: str) -> str:
    if type_ == "vehicle":
        return re.sub(r"[^a-z0-9]", "", s.lower())  # "AP 31 TX 4521" == "AP31TX4521"
    if type_ in ("person", "alias"):
        return norm_name(s)
    return re.sub(r"\s+", " ", s.lower()).strip()


def phonetic(name: str) -> str:
    """Rough key so common South-Indian transliteration variants compare equal
    (Sathya/Satya, Reddy/Reddi, Venkat/Venkata is handled by similarity, not here)."""
    s = norm_name(name).replace(" ", "")
    for a, b in (("th", "t"), ("dh", "d"), ("bh", "b"), ("kh", "k"), ("gh", "g"), ("ph", "f"), ("w", "v"), ("z", "j"),
                 ("ee", "i"), ("oo", "u"), ("y", "i"), ("sh", "s")):
        s = s.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", s)
