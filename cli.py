"""
Интерфейс командной строки и парсер команд
"""

from __future__ import annotations

from typing import List, Tuple
import shlex

from config import APP_NAME, APP_VERSION
from commands import REG
from storage import STORAGE_FILE, load_storage


def parse_input(line: str) -> Tuple[str, List[str]]:
    """
    Разбить команду на имя и аргументы, поддерживая кавычки.

    Примеры:
        'add "John Doe" 1234567890'
        → cmd='add', args=['John Doe', '1234567890']

        'add-note "My Note" Some text here'
        → cmd='add-note', args=['My Note', 'Some', 'text', 'here']

    shlex.split() умеет парсить кавычки как в shell:
    - "текст с пробелами" → один аргумент
    - текст без кавычек → разбивается по пробелам
    """
    try:
        # shlex.split() обрабатывает кавычки как в Unix shell
        parts = shlex.split(line, posix=True)
    except ValueError:
        # Если кавычки неправильные, просто разбиваем по пробелам
        parts = line.split()

    if not parts:
        return "", []
    cmd = parts[0].lower()
    args = parts[1:]
    return cmd, args


def get_all_commands() -> List[str]:
    """Получить список всех доступных команд."""
    return list(REG.all_commands())


def run_cli() -> None:
    """Главный цикл CLI приложения."""
    storage = load_storage()
    print(f"{APP_NAME} v{APP_VERSION}. Type 'help' for commands.")
    print(f"Data stored in: {STORAGE_FILE}\n")

    while True:
        try:
            line = input("enter the command > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        cmd_name, args = parse_input(line)
        resolved = REG.resolve(cmd_name)

        if not resolved:
            print("Unknown command. Type 'help'.")
            continue

        handler = REG.handler(resolved)
        out = handler(args, storage)
        if out == "__EXIT__":
            break
        print(out)

    print("Bye!")
