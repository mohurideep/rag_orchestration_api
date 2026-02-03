def bytes_to_mb(n: int) -> float:
    return round(n / (1024 * 1024), 2)

def mb_to_bytes(n: float) -> int:
    return round(n * (1024 * 1024))