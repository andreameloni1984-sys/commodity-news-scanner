"""Regression test for the production runner's import graph."""


def test_main_runner_imports_and_exposes_run():
    import main

    assert callable(main.run)
