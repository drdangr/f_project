"""
Реєстрація та обробка всіх команд застосунку
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional
import functools

from models import Address, Birthday, Email, Name, Note, Phone, Record
from storage import Storage, save_storage

from datetime import date

# Тип для обробника команди: функція приймає аргументи та сховище, повертає рядок
Handler = Callable[[List[str], Storage], str]


class CommandRegistry:
    """Реєстр команд зі суворим зіставленням за іменем."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Handler] = {}
        self._help: Dict[str, str] = {}
        self._sections: Dict[str, str] = {}
        self._min_args: Dict[str, int] = {}

    def register(
        self, name: str, *, help: str = "", section: str | None = None, min_args: int = 0
    ) -> Callable[[Handler], Handler]:
        """Зареєструвати команду."""

        def decorator(func: Handler) -> Handler:
            key = name.strip().lower()
            if key in self._handlers:
                raise RuntimeError(f"Duplicate command: {name}")
            self._handlers[key] = func
            self._help[key] = help.strip()
            self._min_args[key] = min_args
            normalized_section = section.strip() if section else DEFAULT_SECTION
            if normalized_section not in SECTION_ORDER[:-1]:
                normalized_section = DEFAULT_SECTION
            self._sections[key] = normalized_section
            return func

        return decorator

    def resolve(self, name: str) -> Optional[str]:
        """Повернути точне ім'я команди, якщо воно зареєстроване."""
        k = name.strip().lower()
        return k if k in self._handlers else None

    def handler(self, key: str) -> Handler:
        """Отримати обробник за ключем."""
        return self._handlers[key]

    def validate_args(self, cmd_name: str, args: List[str]) -> None:
        """Перевірити кількість аргументів для команди."""
        key = cmd_name.strip().lower()
        min_required = self._min_args.get(key, 0)
        
        if len(args) < min_required:
            help_text = self._help.get(key, "")
            if help_text:
                raise IndexError(f"Not enough arguments. {help_text}")
            else:
                raise IndexError(f"Command '{cmd_name}' requires at least {min_required} argument(s)")

    def all_commands(self) -> List[str]:
        """Отримати список всіх команд."""
        return sorted(self._handlers.keys())

    def get_help(self, name: str) -> str:
        """Отримати довідку команди за її іменем."""
        key = name.strip().lower()
        return self._help.get(key, "")

    def help_text(self) -> str:
        """Повернути компактний текст довідки."""
        groups: Dict[str, List[str]] = {section: [] for section in SECTION_ORDER}
        for cmd in self.all_commands():
            section = self._sections.get(cmd, DEFAULT_SECTION)
            groups.setdefault(section, []).append(cmd)

        lines = ["Доступні команди:"]
        for section in SECTION_ORDER:
            cmds = groups.get(section, [])
            if not cmds:
                continue
            lines.append("")
            lines.append(f"{section}:")
            for cmd in cmds:
                desc = self._help.get(cmd, "")
                lines.append(f"  - {cmd}: {desc}")

        lines.append("")
        lines.append("Для деталей щодо конкретної команди використовуйте: help <command>")
        return "\n".join(lines)


SECTION_PHONEBOOK = "Phonebook"
SECTION_NOTES = "Notes"
SECTION_SYSTEM = "System"
SECTION_ORDER = [SECTION_PHONEBOOK, SECTION_NOTES, SECTION_SYSTEM, "Прочее"]
DEFAULT_SECTION = SECTION_ORDER[-1]


REG = CommandRegistry()


def input_error(func: Handler) -> Handler:
    """
    Декоратор для обробки помилок та виводу дружніх повідомлень.

    Перехоплює винятки та повертає зрозумілі повідомлення замість краху:
    - KeyError → "Not found: ..." (контакт/нотатка не знайдені)
    - ValueError → "Value error: ..." (неправильне значення, наприклад, поле)
    - IndexError → "Not enough arguments" (мало аргументів)
    - Exception → "Error: ..." (інші помилки)

    Приклад:
        @input_error
        def cmd_example(args, storage):
            if not args:
                raise IndexError("Usage: cmd arg1 arg2")
            if args[0] == "invalid":
                raise ValueError("Invalid argument")
            rec = storage.contacts.get_record(args[0])  # може викинути KeyError
            return "Success"
    """

    @functools.wraps(func)
    def inner(args: List[str], storage: Storage) -> str:
        try:
            return func(args, storage)
        except KeyError as e:
            return f"Not found: '{e.args[0] if e.args else '?'}'."
        except ValueError as e:
            return f"Value error: {e}"
        except IndexError as e:
            return str(e) if str(e) else "Not enough arguments. Use: help"
        except Exception as e:
            return f"Error: {e}"

    return inner


def mutating(func: Handler) -> Handler:
    """
    Декоратор для команд, які змінюють дані (автоматичне збереження).

    Автоматично викликає save_storage() після успішного виконання команди.
    НЕ зберігає якщо:
    - функція повернула помилку (починається з "Error")
    - функція повернула сигнал виходу ("__EXIT__")

    Приклад:
        @mutating
        def cmd_add_contact(args, storage):
            rec = Record(Name(args[0]))
            storage.contacts.add_record(rec)
            return "Contact added"
            # Автоматично викличе save_storage(storage)

        @mutating
        def cmd_invalid(args, storage):
            raise ValueError("Bad input")
            # Не збереже, тому що @input_error поверне "Value error: ..."
    """

    @functools.wraps(func)
    def inner(args: List[str], storage: Storage) -> str:
        result = func(args, storage)
        if result and not result.startswith("Error") and result != "__EXIT__":
            save_storage(storage)
        return result

    return inner


# ==============================
# Контакти
# ==============================


@REG.register(
    "add-contact",
    help='Usage: add-contact "Name" [0123456789]',
    section=SECTION_PHONEBOOK,
    min_args=1,
)
@input_error
@mutating
def cmd_add(args: List[str], storage: Storage) -> str:
    name_arg = args[0]
    phone = Phone(args[1]) if len(args) > 1 else None
    try:
        rec = storage.contacts.get_record(name_arg)
    except KeyError:
        rec = Record(Name(name_arg))
        if phone:
            rec.add_phone(phone)
        storage.contacts.add_record(rec)
        return (
            f"Added contact {rec.name.value} with phone {phone.value}."
            if phone
            else f"Added contact {rec.name.value}."
        )

    if not phone:
        return f"Contact {rec.name.value} already exists. Provide a phone to add."

    if any(p.value == phone.value for p in rec.phones):
        return f"Phone {phone.value} already exists for {rec.name.value}."
    rec.add_phone(phone)
    return f"Phone added for {rec.name.value}."


@REG.register(
    "change-phone",
    help='Usage: change-phone "Name" old10 new10',
    section=SECTION_PHONEBOOK,
    min_args=3,
)
@input_error
@mutating
def cmd_change(args: List[str], storage: Storage) -> str:
    rec = storage.contacts.get_record(args[0])
    rec.edit_phone(args[1], args[2])
    return f"Phone updated for {rec.name.value}."


@REG.register(
    "show-phone",
    help='Usage: show-phone "Name"',
    section=SECTION_PHONEBOOK,
    min_args=1,
)
@input_error
def cmd_phone(args: List[str], storage: Storage) -> str:
    rec = storage.contacts.get_record(args[0])
    if not rec.phones:
        return f"No phone numbers for {rec.name.value}."
    numbers = ", ".join(p.value for p in rec.phones)
    return f"{rec.name.value}: {numbers}"


@REG.register(
    "all-contacts", 
    help="Show all contacts", 
    section=SECTION_PHONEBOOK
)
@input_error
def cmd_all(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    items = storage.contacts.all()
    if not items:
        return "No contacts."
    return "\n".join(str(r) for r in items)


@REG.register(
    "add-birthday",
    help='Usage: add-birthday "Name" DD.MM.YYYY',
    section=SECTION_PHONEBOOK,
    min_args=2,
)
@input_error
@mutating
def cmd_add_birthday(args: List[str], storage: Storage) -> str:
    rec = storage.contacts.get_record(args[0])
    rec.set_birthday(Birthday(args[1]))
    return f"Birthday set for {rec.name.value}."


@REG.register(
    "show-birthday",
    help='Usage: show-birthday "Name"',
    section=SECTION_PHONEBOOK,
    min_args=1,
)
@input_error
def cmd_show_birthday(args: List[str], storage: Storage) -> str:
    rec = storage.contacts.get_record(args[0])
    if not rec.birthday:
        return f"No birthday for {rec.name.value}."
    return f"{rec.name.value}: {rec.birthday.value}"


@REG.register(
    "birthdays",
    help="Show upcoming birthdays (within 7 days)",
    section=SECTION_PHONEBOOK,
)
@input_error
def cmd_birthdays(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    days = 7
    bucket = storage.contacts.upcoming_birthdays(days)
    if not bucket:
        return "No upcoming birthdays."

    today = date.today()
    lines = []
    for delta, items in bucket.items():
        for name, bday, wk in items:
            record = storage.contacts.get_record(name)
            next_bd = record.get_next_birthday(today)
            date_str = next_bd.strftime("%d.%m.%Y")
            if delta == 0:
                lines.append(f"🎉 Congrats {name} — today! ({date_str}, {wk})")
            elif delta == 1:
                lines.append(f"🎉 Congrats {name} — tomorrow! ({date_str}, {wk})")
            else:
                lines.append(f"🎉 Congrats {name} — in {delta} days ({date_str}, {wk})")

    return "\n".join(lines)


@REG.register(
    "add-email",
    help='Usage: add-email "Name" example@mail.com',
    section=SECTION_PHONEBOOK,
    min_args=2,
)
@input_error
@mutating
def cmd_add_email(args: List[str], storage: Storage) -> str:
    rec = storage.contacts.get_record(args[0])
    rec.add_email(Email(args[1]))
    return f"Email added for {rec.name.value}."


@REG.register(
    "delete-email",
    help='Usage: delete-email "Name" example@mail.com',
    section=SECTION_PHONEBOOK,
    min_args=2,
)
@input_error
@mutating
def cmd_remove_email(args: List[str], storage: Storage) -> str:
    rec = storage.contacts.get_record(args[0])
    if rec.remove_email(args[1]):
        return f"Email removed for {rec.name.value}."
    return "Email not found."


@REG.register(
    "add-address",
    help='Usage: add-address "Name" "Kyiv, ..."',
    section=SECTION_PHONEBOOK,
    min_args=2,
)
@input_error
@mutating
def cmd_set_address(args: List[str], storage: Storage) -> str:
    rec = storage.contacts.get_record(args[0])
    # приєдную всі інші аргументи адреси, наприклад "Kyiv, Khreshchatyk 1"
    address_text = " ".join(args[1:]).strip()
    if not address_text:
        raise ValueError('Address cannot be empty.')
    rec.set_address(Address(address_text))
    return f"Address set for {rec.name.value}."


@REG.register(
    "delete-phone",
    help='Usage: delete-phone "Name" 0123456789',
    section=SECTION_PHONEBOOK,
    min_args=2,
)
@input_error
@mutating
def cmd_remove_phone(args: List[str], storage: Storage) -> str:
    rec = storage.contacts.get_record(args[0])
    if rec.remove_phone(args[1]):
        return f"Phone removed for {rec.name.value}."
    return "Phone not found."


@REG.register(
    "delete-address",
    help='Usage: delete-address "Name"',
    section=SECTION_PHONEBOOK,
    min_args=1,
)
@input_error
@mutating
def cmd_remove_address(args: List[str], storage: Storage) -> str:
    rec = storage.contacts.get_record(args[0])
    if rec.remove_address():
        return f"Address removed for {rec.name.value}."
    return "No address to remove."


@REG.register(
    "find-contact", help="Usage: find-contact query", section=SECTION_PHONEBOOK, min_args=1
)
@input_error
def cmd_find(args: List[str], storage: Storage) -> str:
    res = storage.contacts.search(args[0])
    return "\n".join(str(r) for r in res) if res else "No results."


@REG.register(
    "delete-contact",
    help='Usage: delete-contact "Name"',
    section=SECTION_PHONEBOOK,
    min_args=1,
)
@input_error
@mutating
def cmd_delete_contact(args: List[str], storage: Storage) -> str:
    if storage.contacts.remove_record(args[0]):
        return f"Deleted contact '{args[0]}'."
    return "Contact not found."


# ==============================
# Нотатки
# ==============================


@REG.register(
    "add-note",
    help='Usage: add-note "Title" text...',
    section=SECTION_NOTES,
    min_args=2,
)
@input_error
@mutating
def cmd_add_note(args: List[str], storage: Storage) -> str:
    text = " ".join(args[1:]).strip()
    if not text:
        raise ValueError("Note text cannot be empty.")
    note = Note(title=args[0], text=text)
    storage.notes.add(note)
    return f"Note added: {args[0]}"


@REG.register(
    "all-notes",
    help="List all notes (sort by title or created)",
    section=SECTION_NOTES,
)
@input_error
def cmd_list_notes(args: List[str], storage: Storage) -> str:
    sort_by = (args[0] if args else "title").strip().lower()
    items = storage.notes.all(sort_by=sort_by)
    if not items:
        return "No notes."
    out = []
    for n in items:
        tgs = ("#" + " #".join(sorted(n.tags))) if n.tags else "(no tags)"
        out.append(f"{n.title} [{tgs}] — {n.created:%Y-%m-%d %H:%M}\n{n.text}")
    separator = "\n" + "-" * 40 + "\n"
    return separator + separator.join(out) + separator


@REG.register(
    "find-note",
    help="Usage: find-note query",
    section=SECTION_NOTES,
    min_args=1,
)
@input_error
def cmd_find_note(args: List[str], storage: Storage) -> str:
    res = storage.notes.search_text(args[0])
    if not res:
        return "No results."
    out = []
    for n in res:
        #tgs = ("#" + " #".join(sorted(n.tags))) if n.tags else "(no tags)"
        if n.tags:
            sorted_tags = sorted(n.tags)
            formatted_tags = " #".join(sorted_tags)
            tgs = f"#{formatted_tags}"
        else:
            tgs = "(no tags)"
        out.append(f"{n.title} [{tgs}]\n{n.text}")
    separator = "\n" + "-" * 40 + "\n"
    return separator + separator.join(out) + separator


@REG.register(
    "find-tag",
    help="Usage: find-tag tag",
    section=SECTION_NOTES,
    min_args=1,
)
@input_error
def cmd_find_tag(args: List[str], storage: Storage) -> str:
    res = storage.notes.search_tag(args[0])
    if not res:
        return "No results."
    out = []
    for n in res:
        tgs = ("#" + " #".join(sorted(n.tags))) if n.tags else "(no tags)"
        out.append(f"{n.title} [{tgs}]\n{n.text}")
    separator = "\n" + "-" * 40 + "\n"
    return separator + separator.join(out) + separator


@REG.register(
    "edit-note",
    help='Usage: edit-note "Title" new_text...',
    section=SECTION_NOTES,
    min_args=2,
)
@input_error
@mutating
def cmd_edit_note(args: List[str], storage: Storage) -> str:
    note = storage.notes.get_note(args[0])
    new_text = " ".join(args[1:]).strip()
    if not new_text:
        raise ValueError("Note text cannot be empty.")
    note.text = new_text
    return f"Note updated: {args[0]}"


@REG.register(
    "add-tags",
    help='Usage: add-tags "Title" tag1 tag2 ...',
    section=SECTION_NOTES,
    min_args=2,
)
@input_error
@mutating
def cmd_tag_add(args: List[str], storage: Storage) -> str:
    note = storage.notes.get_note(args[0])
    note.add_tags(*args[1:])
    return f"Tags added to '{args[0]}': {', '.join(sorted(args[1:]))}"


@REG.register(
    "delete-tag",
    help='Usage: delete-tag "Title" tag',
    section=SECTION_NOTES,
    min_args=2,
)
@input_error
@mutating
def cmd_tag_remove(args: List[str], storage: Storage) -> str:
    note = storage.notes.get_note(args[0])
    if note.remove_tag(args[1]):
        return f"Tag removed from '{args[0]}'."
    return "Tag not found."


@REG.register(
    "delete-note",
    help='Usage: delete-note "Title"',
    section=SECTION_NOTES,
    min_args=1,
)
@input_error
@mutating
def cmd_delete_note(args: List[str], storage: Storage) -> str:
    if storage.notes.remove(args[0]):
        return f"Deleted note '{args[0]}'."
    return "Note not found."


# ==============================
# Система
# ==============================


@REG.register("hello", help="Greeting from bot", section=SECTION_SYSTEM)
@input_error
def cmd_hello(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    return "Привіт! Чим можу допомогти?"


@REG.register("help", help="Show help", section=SECTION_SYSTEM)
@input_error
def cmd_help(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    if args:
        key = args[0].strip().lower()
        resolved = REG.resolve(key)
        if not resolved:
            return f"Unknown command: '{args[0]}'"
        desc = REG.get_help(resolved)
        return f"Command: {resolved}\nDescription: {desc}"
    return REG.help_text()


@REG.register("close", help="Close program", section=SECTION_SYSTEM)
@REG.register("exit", help="Close program", section=SECTION_SYSTEM)
@input_error
def cmd_exit(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    return "__EXIT__"


@REG.register("version", help="Show version", section=SECTION_SYSTEM)
@input_error
def cmd_version(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    from config import APP_NAME, APP_VERSION
    from storage import STORAGE_FILE

    return f"{APP_NAME} v{APP_VERSION} | data: {STORAGE_FILE}"
