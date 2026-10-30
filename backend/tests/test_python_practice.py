import pytest

from app.services.python_practice import PracticeError, run_practice


def test_runs_basic_assignments_loops_and_print():
    assert run_practice("total = 0\nfor n in range(4):\n    total = total + n\nprint(total)") == "6"


def test_blocks_imports_and_unsupported_calls():
    with pytest.raises(PracticeError):
        run_practice("import os")
    with pytest.raises(PracticeError):
        run_practice("open('secret.txt')")


def test_limits_output():
    with pytest.raises(PracticeError, match="limited to 12,000 characters"):
        run_practice("print('x' * 13000)")
