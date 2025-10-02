def normalize_tac(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines() if line.strip())