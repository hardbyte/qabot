import pytest
from examples import example1, example2, example3

def test_example1():
    result = example1.main()
    assert result == "Expected output from example1"

def test_example2():
    result = example2.main()
    assert result == "Expected output from example2"

def test_example3():
    result = example3.main()
    assert result == "Expected output from example3"