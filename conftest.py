"""Configure pytest. This file exists so that linting can pass even when there are no tests."""


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ANN001
    """Disable warnings-as-workflow errors; our upstream dependencies raise warnings."""
    if exitstatus == 5:  # noqa: PLR2004
        session.exitstatus = 0
