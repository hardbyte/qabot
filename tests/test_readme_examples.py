import pytest
import sys
from io import StringIO
from contextlib import contextmanager
from examples import example_1, example_2, example_3

@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

def test_example_1():
    with captured_output() as (out, err):
        example_1.main()
    output = out.getvalue().strip()
    assert output == "Hello, World!"

def test_example_2():
    with captured_output() as (out, err):
        example_2.main()
    output = out.getvalue().strip()
    assert output == "This is a more complex example."

def test_example_3():
    with captured_output() as (out, err):
        example_3.main()
    output = out.getvalue().strip()
    assert output == "This example demonstrates a more involved coding process."
