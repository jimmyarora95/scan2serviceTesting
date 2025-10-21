#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def _bootstrap_local_venv():
    """Ensure the project-local virtualenv is on sys.path when not activated."""
    base_dir = Path(__file__).resolve().parent
    venv_dir = base_dir / ".venv"
    if not venv_dir.exists():
        return

    candidate_paths = []
    win_site = venv_dir / "Lib" / "site-packages"
    if win_site.exists():
        candidate_paths.append(win_site)
    candidate_paths.extend(venv_dir.glob("lib/python*/site-packages"))

    for site_packages in candidate_paths:
        site_path = str(site_packages)
        if site_path not in sys.path:
            sys.path.insert(0, site_path)


_bootstrap_local_venv()


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scan2service.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
