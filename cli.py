"""
Інтерфейс командного рядка та парсер команд
"""

from __future__ import annotations

from typing import List, Tuple
import shlex

from config import APP_NAME, APP_VERSION
from commands import REG
from storage import STORAGE_FILE, load_storage
# ЗМІНЕНО: додано імпорт кольорових помічників
from color_helper import ICON_BOT, BADGE_ERROR, BADGE_ASSISTANT, colored_error

# ----prompt_toolkit для автокомпліту команд ----
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit import PromptSession


class HintsCompleter(Completer):
    def __init__(self, hints, get_contacts_func=None):
        self.hints = tuple(sorted(set(hints)))
        self.get_contacts_func = get_contacts_func  # optional callback

    def get_completions(self, document, complete_event):
        tb = document.text_before_cursor           # <-- no .strip()
        word = document.get_word_before_cursor()
        tokens = tb.split()
        ends_with_space = tb.endswith(" ")

        # --- First token (command) completion ---
        # Cases considered "still typing the command":
        #   ""                      -> no tokens yet
        #   "ad"                    -> 1 token, no trailing space
        #   "add"                   -> 1 token, no trailing space
        if not tokens or (len(tokens) == 1 and not ends_with_space):
            low = word.lower()
            for hint in self.hints:
                if hint.startswith(low):
                    yield Completion(hint, start_position=-len(word))
            return

        # --- Argument completion (after first space) ---
        command = tokens[0].lower()
        if command in ("add-contact", "change-phone", "show-phone", "add-birthday"
                       , "show-birthday","add-email", "delete-email","add-address", "delete-contact"
                       ,"delete-phone","delete-address"):
            if self.get_contacts_func:
                low = word.lower()
                for name in self.get_contacts_func():
                    if name.lower().startswith(low):
                        yield Completion(name, start_position=-len(word))


def parse_input(line: str) -> Tuple[str, List[str]]:
    """
    Розбити команду на ім'я та аргументи, підтримуючи лапки.

    Приклади:
        'add "John Doe" 1234567890'
        → cmd='add', args=['John Doe', '1234567890']

        'add-note "My Note" Some text here'
        → cmd='add-note', args=['My Note', 'Some', 'text', 'here']

    shlex.split() вміє парсити лапки як у shell:
    - "текст з пробілами" → один аргумент
    - текст без лапок → розбивається за пробілами
    """
    try:
        # shlex.split() обробляє лапки як в Unix shell
        parts = shlex.split(line, posix=True)
    except ValueError:
        # Якщо лапки неправильні, просто розбиваємо за пробілами
        parts = line.split()

    if not parts:
        return "", []
    cmd = parts[0].lower()
    args = parts[1:]
    return cmd, args


def get_all_commands() -> List[str]:
    """Отримати список всіх доступних команд."""
    return list(REG.all_commands())


# отримання імен контактів зі сховища динамічно
def get_contact_names(storage):
    """
    Return a list of contact display names from storage.contacts (AddressBook).
    Handles both API-based (.all()) and dict-backed (.data / ._data) implementations.
    """
    names = []

    try:
        ab = storage.contacts  # AddressBook
    except AttributeError:
        return []

    # Case 1: AddressBook has .all() returning Record objects
    try:
        for rec in ab.all():
            n = getattr(rec, "name", None)
            n = getattr(n, "value", n)
            if n:
                names.append(str(n))
    except Exception:
        pass

    # Case 2: dict-like .data / ._data with Record values
    for attr in ("data", "_data"):
        d = getattr(ab, attr, None)
        if isinstance(d, dict):
            for rec in d.values():
                n = getattr(rec, "name", None)
                n = getattr(n, "value", n)
                if n:
                    names.append(str(n))

    # Видалення дублікатів та повернення
    seen, uniq = set(), []
    for n in names:
        if n and n not in seen:
            uniq.append(n)
            seen.add(n)

    return uniq


def run_cli() -> None:
    storage = load_storage()
    # ЗМІНЕНО: Додано іконку бота після APP_NAME
    print(f"{APP_NAME} {ICON_BOT} v{APP_VERSION}. Type 'help' for commands.")
    print(f"Data stored in: {STORAGE_FILE}\n")

    session = PromptSession()

    # Debug
    #print("DEBUG contact names:", get_contact_names(storage))

    completer = HintsCompleter(
        hints=get_all_commands(),
        get_contacts_func=lambda: get_contact_names(storage)
    )

    while True:
        try:
            line = session.prompt(
                "enter the command > ",
                completer=completer,
                complete_while_typing=True
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        cmd_name, args = parse_input(line)
        resolved = REG.resolve(cmd_name)

        if not resolved:
            # ЗМІНЕНО: Додано помилку-бейдж та червоний колір для невідомих команд
            error_msg = "Unknown command. Type 'help'."
            print(f"{BADGE_ERROR} {colored_error(error_msg)}")
            continue

        try:
            REG.validate_args(resolved, args)
            handler = REG.handler(resolved)
            out = handler(args, storage)
        except IndexError as e:
            # ЗМІНЕНО: Додано помилку-бейдж та червоний колір для помилок індексу
            out = f"{BADGE_ERROR} {colored_error(str(e))}"
        
        if out == "__EXIT__": break
        # ЗМІНЕНО: Виведення з бейджем асистента, якщо це не помилка
        if not out.startswith(f"{BADGE_ERROR}"):
            print(f"{BADGE_ASSISTANT} {out}")
        else:
            print(out)

    # ЗМІНЕНО: Додано іконку 
    print("👋 Bye!")

