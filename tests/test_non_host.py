from __future__ import annotations

import json
import sys
from platform import python_implementation
from typing import TYPE_CHECKING

import pytest
import virtualenv

from pipdeptree.__main__ import main

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("args_joined", [True, False])
def test_custom_interpreter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    args_joined: bool,
) -> None:
    result = virtualenv.cli_run([str(tmp_path / "venv"), "--activators", ""])
    cmd = [sys.executable]
    monkeypatch.chdir(tmp_path)
    py = str(result.creator.exe.relative_to(tmp_path))
    cmd += [f"--python={result.creator.exe}"] if args_joined else ["--python", py]
    monkeypatch.setattr(sys, "argv", [*cmd, "-j"])
    main()
    out, _ = capfd.readouterr()
    found = {i["package"]["package_name"] for i in json.loads(out)}
    implementation = python_implementation()
    if implementation == "CPython":  # pragma: pypy
        expected = {"pip", "setuptools", "wheel"}
    elif implementation == "PyPy":  # pragma: python
        # hpy added in 7.3.2, enabled in 7.3.3
        if sys.pypy_version_info >= (7, 3, 3):  # type: ignore[attr-defined] # pragma: pypy-lt-733
            expected = {"cffi", "greenlet", "hpy", "pip", "readline", "setuptools", "wheel"}
        else:  # pragma: pypy-gte-733
            expected = {"cffi", "greenlet", "pip", "readline", "setuptools", "wheel"}
    else:
        raise ValueError(implementation)
    if sys.version_info >= (3, 12):
        expected -= {"setuptools", "wheel"}
    assert found == expected, out

    monkeypatch.setattr(sys, "argv", [*cmd, "--graph-output", "something"])
    with pytest.raises(SystemExit) as context:
        main()
    out, err = capfd.readouterr()
    assert context.value.code == 1
    assert not out
    assert err == "graphviz functionality is not supported when querying non-host python\n"
