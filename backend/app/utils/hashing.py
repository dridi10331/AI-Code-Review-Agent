import hashlib


def normalized_code_hash(code: str, language: str) -> str:
    normalized = "\n".join(line.rstrip() for line in code.splitlines()).strip()
    payload = f"{language.lower()}::{normalized}".encode()
    return hashlib.sha256(payload).hexdigest()
