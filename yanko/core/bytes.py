

def nearest_bytes(n):
    p = int(float(n).hex().split('p+')[1]) + 1
    return 2 ** p
