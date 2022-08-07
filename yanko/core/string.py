from hashlib import blake2b

def name_to_code(value: str):
    return value.translate(str.maketrans(dict.fromkeys('aeiouAEIOU')))

def string_hash(s):
    h = blake2b(digest_size=20)
    h.update(s.encode())
    return h.hexdigest()


def truncate(value: str, size=20, ellipsis="..."):
    value = value.strip()
    if not len(value) > size:
        return value
    limit = size - len(ellipsis)
    cut = value[:limit]
    return f"{cut}{ellipsis}"
