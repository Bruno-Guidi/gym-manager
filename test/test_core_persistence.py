import logging

import pytest

from gym_manager.core.base import Number
from gym_manager.core.persistence import LRUCache


def test_LRUCache_getItem_raisesTypeError():
    cache = LRUCache(int, value_type=str, max_len=3)
    with pytest.raises(TypeError):
        value = cache["abc"]


def test_LRUCache_getItem_raisesKeyError():
    cache = LRUCache(key_type=int, value_type=str, max_len=3)
    with pytest.raises(KeyError):
        value = cache[123]


def test_LRUCache_iter_completeIteration():
    cache = LRUCache(key_type=int, value_type=int, max_len=3)
    keys = [i for i in range(3)]
    for i in keys:
        cache[i] = i

    # The keys list should be reversed, because the keys in the cache are stored in LRU order, meaning 3 is the LRU.
    keys.reverse()
    assert [key for key in cache] == keys


def test_LRUCache_iter_completeIteration_zeroKeys():
    cache = LRUCache(key_type=int, value_type=int, max_len=3)

    assert [] == [key for key in cache]


def test_LRUCache_iter_keyContained():
    cache = LRUCache(key_type=int, value_type=int, max_len=3)
    cache[5] = 5
    assert 5 in cache

    cache[2] = 2
    cache[3] = 3
    cache[5] = 5  # The key 5 is moved to the first position.
    cache[1] = 1  # When this key is inserted, the key 2 should be discarded.
    assert (5 in cache) and (2 not in cache)


def test_LRUCache_iter_keyNotContained():
    cache = LRUCache(key_type=int, value_type=int, max_len=3)

    assert 5 not in cache

    cache[5] = 5
    cache[2] = 2
    cache[3] = 3
    cache[1] = 1

    assert 5 not in cache


def test_LRUCache_getItem_maxLenIsNeverExceeded():
    max_len = 3
    cache = LRUCache(key_type=int, value_type=int, max_len=max_len)

    cache[1] = 1
    assert len(cache) <= max_len
    cache[2] = 2
    assert len(cache) <= max_len
    cache[3] = 3
    assert len(cache) <= max_len
    cache[4] = 4
    assert len(cache) <= max_len


def test_LRUCache_getItem_correctlyReturned():
    max_len = 3
    cache = LRUCache(key_type=int, value_type=int, max_len=max_len)

    cache[1] = 1
    assert cache[1] == 1

    cache[1] = 3
    assert cache[1] == 3


def test_LRUCache_pop_raisesTypeError():
    cache = LRUCache(key_type=int, value_type=int, max_len=3)
    with pytest.raises(TypeError):
        cache.pop("abc")


def test_LRUCache_pop_raisesKeyError():
    cache = LRUCache(key_type=int, value_type=int, max_len=3)
    with pytest.raises(KeyError):
        cache.pop(2)


def test_LRUCache_pop_lenReduced():
    cache = LRUCache(key_type=int, value_type=int, max_len=3)
    cache[1] = 1
    cache[2] = 2
    assert len(cache) == 2

    cache.pop(1)
    assert len(cache) == 1

    cache.pop(2)
    assert len(cache) == 0


def test_LRUCache_setItem_raisesTypeError():
    cache = LRUCache(key_type=int, value_type=int, max_len=3)

    with pytest.raises(TypeError):
        cache[Number(1)] = 1

    with pytest.raises(TypeError):
        cache[1] = Number(1)


def test_LRUCache_moveToFront():
    max_len = 3
    cache = LRUCache(key_type=int, value_type=int, max_len=max_len)

    cache[1] = 1
    cache[2] = 2
    cache[3] = 3

    cache.move_to_front(2)

    assert [2, 3, 1] == [key for key in cache]
