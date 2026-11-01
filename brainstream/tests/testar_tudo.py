"""Executor central da suíte de testes Django."""

import os
import sys
from pathlib import Path

from django.core.management import execute_from_command_line


def main():
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brainstream.settings')
    execute_from_command_line([sys.argv[0], 'test', *sys.argv[1:]])


if __name__ == '__main__':
    main()
