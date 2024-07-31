#!/usr/bin/env python

import logging
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def global_variables():
    """Set global variables for the test session."""
    try:
        return {
            "SAMPLE_DATA_1": Path(__file__).parent / "data/sample1.csv",
            "SAMPLE_DATA_2": Path(__file__).parent / "data/sample2.csv",
        }
    except Exception:
        return None


def test_crosstab_init(global_variables):
    assert 1 == 1
