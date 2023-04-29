import sys
import os
import numpy as np
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{dir_path}/..")
from pyfive import util


def test_2comp():
    num = -1
    ret = util.complement_code(num, 32)
    assert(ret == np.uint32(num))
    num = -12953
    ret = util.complement_code(num, 32)
    assert(ret == np.uint32(num))
    num = 4645345
    ret = util.complement_code(num, 32)
    assert(ret == np.uint32(num))
    num = -1
    ret = util.complement_code(num, 8)
    assert(ret == np.uint8(num))
    num = -128
    ret = util.complement_code(num, 8)
    assert(ret == np.uint8(num))
    num = 127
    ret = util.complement_code(num, 8)
    assert(ret == np.uint8(num))
    num = 0
    ret = util.complement_code(num, 8)
    assert(ret == np.uint8(num))
    num = 233
    ret = util.complement_code(num, 8)
    assert(ret == np.uint8(num))


def test_origcode():
    num = 255
    ret = util.original_code(num, 8)
    assert(ret == np.int8(num))
    num = -1
    ret = util.original_code(num, 8)
    assert(ret == np.int8(num))
    num = 127
    ret = util.original_code(num, 8)
    assert(ret == np.int8(num))
    num = 128
    ret = util.original_code(num, 8)
    assert(ret == np.int8(num))
    num = -128
    ret = util.original_code(num, 8)
    assert(ret == np.int8(num))
    num = 0
    ret = util.original_code(num, 8)
    assert(ret == np.int8(num))
