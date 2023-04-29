def complement_code(num, bits):
    return (num + (1 << bits)) & ((1 << bits) - 1)


# ((255+128)&0xff)-128 is -1
def original_code(num, bits):
    return ((num+(1 << bits - 1)) & ((1 << bits) - 1)) - (1 << bits - 1)
