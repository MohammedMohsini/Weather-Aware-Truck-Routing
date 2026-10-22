from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_production_settings_require_secret_key() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.update({'DEBUG': 'False', 'SECRET_KEY': ''})

    result = subprocess.run(
        [sys.executable, '-c', 'import config.settings'],
        cwd=backend_dir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert 'SECRET_KEY must be set when DEBUG is False.' in result.stderr


def test_debug_is_disabled_by_default() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.pop('DEBUG', None)
    environment.update({'SECRET_KEY': 'test-secret-key', 'PYTHON_DOTENV_DISABLED': '1'})

    result = subprocess.run(
        [sys.executable, '-c', 'from config.settings import DEBUG; print(DEBUG)'],
        cwd=backend_dir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == 'False'
