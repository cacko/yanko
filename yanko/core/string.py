


def name_to_code(value: str):
    return value.translate(str.maketrans(dict.fromkeys('aeiouAEIOU')))