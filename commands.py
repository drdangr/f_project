"""
Регистрация и обработка всех команд приложения
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional
import functools

from models import Address, Birthday, Email, Name, Note, Phone, Record
from storage import Storage, save_storage


# Тип для обработчика команды: функция принимает аргументы и хранилище, возвращает строку
Handler = Callable[[List[str], Storage], str]


class CommandRegistry:
    """Реестр команд со строгим сопоставлением по имени."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Handler] = {}
        self._help: Dict[str, str] = {}
        self._sections: Dict[str, str] = {}

    def register(
        self, name: str, *, help: str = "", section: str | None = None
    ) -> Callable[[Handler], Handler]:
        """Зарегистрировать команду."""

        def decorator(func: Handler) -> Handler:
            key = name.strip().lower()
            if key in self._handlers:
                raise RuntimeError(f"Duplicate command: {name}")
            self._handlers[key] = func
            self._help[key] = help.strip()
            normalized_section = section.strip() if section else DEFAULT_SECTION
            if normalized_section not in SECTION_ORDER[:-1]:
                normalized_section = DEFAULT_SECTION
            self._sections[key] = normalized_section
            return func

        return decorator

    def resolve(self, name: str) -> Optional[str]:
        """Вернуть точное имя команды, если оно зарегистрировано."""
        k = name.strip().lower()
        return k if k in self._handlers else None

    def handler(self, key: str) -> Handler:
        """Получить обработчик по ключу."""
        return self._handlers[key]

    def all_commands(self) -> List[str]:
        """Получить список всех команд."""
        return sorted(self._handlers.keys())

    def get_help(self, name: str) -> str:
        """Получить справку команды по её имени."""
        key = name.strip().lower()
        return self._help.get(key, "")

    def help_text(self) -> str:
        """Вернуть компактный текст справки."""
        groups: Dict[str, List[str]] = {section: [] for section in SECTION_ORDER}
        for cmd in self.all_commands():
            section = self._sections.get(cmd, DEFAULT_SECTION)
            groups.setdefault(section, []).append(cmd)

        lines = ["Доступные команды:"]
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
        lines.append("Для деталей по конкретной команде используйте: help <command>")
        return "\n".join(lines)


SECTION_PHONEBOOK = "Телефонная книга"
SECTION_NOTES = "Заметки"
SECTION_SYSTEM = "Система"
SECTION_ORDER = [SECTION_PHONEBOOK, SECTION_NOTES, SECTION_SYSTEM, "Прочее"]
DEFAULT_SECTION = SECTION_ORDER[-1]


REG = CommandRegistry()


def require_args(
    args: List[str], count: int, usage: str = "Not enough arguments"
) -> None:
    """Проверить, что есть нужное количество аргументов."""
    if len(args) < count:
        raise IndexError(usage)


def input_error(func: Handler) -> Handler:
    """
    Декоратор для обработки ошибок и вывода дружных сообщений.

    Перехватывает исключения и возвращает понятные сообщения вместо краша:
    - KeyError → "Not found: ..." (контакт/заметка не найдены)
    - ValueError → "Value error: ..." (неправильное значение, например, поле)
    - IndexError → "Not enough arguments" (мало аргументов)
    - Exception → "Error: ..." (прочие ошибки)

    Пример:
        @input_error
        def cmd_example(args, storage):
            if not args:
                raise IndexError("Usage: cmd arg1 arg2")
            if args[0] == "invalid":
                raise ValueError("Invalid argument")
            rec = storage.contacts.get_record(args[0])  # может выбросить KeyError
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
    Декоратор для команд, которые меняют данные (автоматическое сохранение).

    Автоматически вызывает save_storage() после успешного выполнения команды.
    НЕ сохраняет если:
    - функция вернула ошибку (начинается с "Error")
    - функция вернула сигнал выхода ("__EXIT__")

    Пример:
        @mutating
        def cmd_add_contact(args, storage):
            rec = Record(Name(args[0]))
            storage.contacts.add_record(rec)
            return "Contact added"
            # Автоматически вызовет save_storage(storage)

        @mutating
        def cmd_invalid(args, storage):
            raise ValueError("Bad input")
            # Не сохранит, потому что @input_error вернёт "Value error: ..."
    """

    @functools.wraps(func)
    def inner(args: List[str], storage: Storage) -> str:
        result = func(args, storage)
        if result and not result.startswith("Error") and result != "__EXIT__":
            save_storage(storage)
        return result

    return inner


# ==============================
# Контакты
# ==============================


@REG.register(
    "add",
    help='Додати контакт або телефон: add "Name" [0123456789]',
    section=SECTION_PHONEBOOK,
)
@input_error
@mutating
def cmd_add(args: List[str], storage: Storage) -> str:
    require_args(args, 1, 'Usage: add "Name" [0123456789]')
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
    "change",
    help='Змінити телефон: change "Name" old10 new10',
    section=SECTION_PHONEBOOK,
)
@input_error
@mutating
def cmd_change(args: List[str], storage: Storage) -> str:
    require_args(args, 3, 'Usage: change "Name" old10 new10')
    rec = storage.contacts.get_record(args[0])
    rec.edit_phone(args[1], args[2])
    return f"Phone updated for {rec.name.value}."


@REG.register(
    "phone",
    help='Показать телефоны контакта: phone "Name"',
    section=SECTION_PHONEBOOK,
)
@input_error
def cmd_phone(args: List[str], storage: Storage) -> str:
    require_args(args, 1, 'Usage: phone "Name"')
    rec = storage.contacts.get_record(args[0])
    if not rec.phones:
        return f"No phone numbers for {rec.name.value}."
    numbers = ", ".join(p.value for p in rec.phones)
    return f"{rec.name.value}: {numbers}"


@REG.register("all", help="Показать все контакты: all", section=SECTION_PHONEBOOK)
@input_error
def cmd_all(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    items = storage.contacts.all()
    if not items:
        return "No contacts."
    return "\n".join(str(r) for r in items)


@REG.register(
    "add-birthday",
    help='Додати ДР: add-birthday "Name" DD.MM.YYYY',
    section=SECTION_PHONEBOOK,
)
@input_error
@mutating
def cmd_add_birthday(args: List[str], storage: Storage) -> str:
    require_args(args, 2, 'Usage: add-birthday "Name" DD.MM.YYYY')
    rec = storage.contacts.get_record(args[0])
    rec.set_birthday(Birthday(args[1]))
    return f"Birthday set for {rec.name.value}."


@REG.register(
    "show-birthday",
    help='Показать ДР: show-birthday "Name"',
    section=SECTION_PHONEBOOK,
)
@input_error
def cmd_show_birthday(args: List[str], storage: Storage) -> str:
    require_args(args, 1, 'Usage: show-birthday "Name"')
    rec = storage.contacts.get_record(args[0])
    if not rec.birthday:
        return f"No birthday for {rec.name.value}."
    return f"{rec.name.value}: {rec.birthday.value}"


@REG.register(
    "birthdays",
    help="Дні народження протягом тижня: birthdays",
    section=SECTION_PHONEBOOK,
)
@input_error
def cmd_birthdays(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    days = 7
    bucket = storage.contacts.upcoming_birthdays(days)
    if not bucket:
        return "No upcoming birthdays."

    weekday_names = {
        0: "Today",
        1: "Tomorrow",
        **{i: f"+{i} days" for i in range(2, days + 1)},
    }
    lines = []
    for delta, items in bucket.items():
        lines.append(f"{weekday_names.get(delta, f'+{delta} days')}:")
        for name, bday, wk in items:
            lines.append(f"  {name} — {bday} ({wk})")
    return "\n".join(lines)


@REG.register(
    "add-email",
    help='Добавить email: add-email "Name" example@mail.com',
    section=SECTION_PHONEBOOK,
)
@input_error
@mutating
def cmd_add_email(args: List[str], storage: Storage) -> str:
    require_args(args, 2, 'Usage: add-email "Name" example@mail.com')
    rec = storage.contacts.get_record(args[0])
    rec.add_email(Email(args[1]))
    return f"Email added for {rec.name.value}."


@REG.register(
    "remove-email",
    help='Удалить email: remove-email "Name" example@mail.com',
    section=SECTION_PHONEBOOK,
)
@input_error
@mutating
def cmd_remove_email(args: List[str], storage: Storage) -> str:
    require_args(args, 2, 'Usage: remove-email "Name" example@mail.com')
    rec = storage.contacts.get_record(args[0])
    if rec.remove_email(args[1]):
        return f"Email removed for {rec.name.value}."
    return "Email not found."


@REG.register(
    "set-address",
    help='Вкажіть адресу: set-address "Name" "Kyiv, ..."',
    section=SECTION_PHONEBOOK,
)
@input_error
@mutating
def cmd_set_address(args: List[str], storage: Storage) -> str:
    require_args(args, 2, 'Usage: set-address "Name" "Kyiv, ..."')
    rec = storage.contacts.get_record(args[0])
    # приєдную всі інші аргументи адреси, e.g. "Kyiv, Khreshchatyk 1"
    address_text = " ".join(args[1:]).strip()
    if not address_text:
        raise ValueError('Address cannot be empty.')
    rec.set_address(Address(address_text))
    return f"Address set for {rec.name.value}."


@REG.register(
    "find", help="Поиск контактов: find query", section=SECTION_PHONEBOOK
)
@input_error
def cmd_find(args: List[str], storage: Storage) -> str:
    require_args(args, 1, "Usage: find query")
    res = storage.contacts.search(args[0])
    return "\n".join(str(r) for r in res) if res else "No results."


@REG.register(
    "delete-contact",
    help='Удалить контакт: delete-contact "Name"',
    section=SECTION_PHONEBOOK,
)
@input_error
@mutating
def cmd_delete_contact(args: List[str], storage: Storage) -> str:
    require_args(args, 1, 'Usage: delete-contact "Name"')
    if storage.contacts.remove_record(args[0]):
        return f"Deleted contact '{args[0]}'."
    return "Contact not found."


# ==============================
# Заметки
# ==============================


@REG.register(
    "add-note",
    help='Добавить заметку: add-note "Title" текст...',
    section=SECTION_NOTES,
)
@input_error
@mutating
def cmd_add_note(args: List[str], storage: Storage) -> str:
    require_args(args, 2, 'Usage: add-note "Title" текст...')
    text = " ".join(args[1:]).strip()
    if not text:
        raise ValueError("Note text cannot be empty.")
    note = Note(title=args[0], text=text)
    storage.notes.add(note)
    return f"Note added: {args[0]}"


@REG.register(
    "list-notes",
    help="Показать заметки: list-notes [title|created]",
    section=SECTION_NOTES,
)
@input_error
def cmd_list_notes(args: List[str], storage: Storage) -> str:
    sort_by = args[0] if args else "title"
    items = storage.notes.all(sort_by=sort_by)
    if not items:
        return "No notes."
    out = []
    for n in items:
        tgs = ("#" + " #".join(sorted(n.tags))) if n.tags else "(no tags)"
        out.append(f"{n.title} [{tgs}] — {n.created:%Y-%m-%d %H:%M}\n{n.text}")
    return "\n\n---\n\n".join(out)


@REG.register(
    "find-note",
    help="Поиск заметок по тексту: find-note query",
    section=SECTION_NOTES,
)
@input_error
def cmd_find_note(args: List[str], storage: Storage) -> str:
    require_args(args, 1, "Usage: find-note query")
    res = storage.notes.search_text(args[0])
    return (
        "\n\n---\n\n".join(f"{n.title}:\n{n.text}" for n in res)
        if res
        else "No results."
    )


@REG.register(
    "find-tag",
    help="Поиск заметок по тегу: find-tag tag",
    section=SECTION_NOTES,
)
@input_error
def cmd_find_tag(args: List[str], storage: Storage) -> str:
    require_args(args, 1, "Usage: find-tag tag")
    res = storage.notes.search_tag(args[0])
    return (
        "\n\n---\n\n".join(
            f"{n.title} [#" + " #".join(sorted(n.tags)) + "]\n" + n.text for n in res
        )
        if res
        else "No results."
    )


@REG.register(
    "edit-note",
    help='Редактировать заметку: edit-note "Title" новий_текст...',
    section=SECTION_NOTES,
)
@input_error
@mutating
def cmd_edit_note(args: List[str], storage: Storage) -> str:
    require_args(args, 2, 'Usage: edit-note "Title" новий_текст...')
    note = storage.notes.get_note(args[0])
    new_text = " ".join(args[1:]).strip()
    if not new_text:
        raise ValueError("Note text cannot be empty.")
    note.text = new_text
    return f"Note updated: {args[0]}"


@REG.register(
    "tag-add",
    help='Добавить теги: tag-add "Title" tag1 tag2 ...',
    section=SECTION_NOTES,
)
@input_error
@mutating
def cmd_tag_add(args: List[str], storage: Storage) -> str:
    require_args(args, 2, 'Usage: tag-add "Title" tag1 tag2 ...')
    note = storage.notes.get_note(args[0])
    note.add_tags(*args[1:])
    return f"Tags added to '{args[0]}': {', '.join(sorted(args[1:]))}"


@REG.register(
    "tag-remove",
    help='Удалить тег: tag-remove "Title" tag',
    section=SECTION_NOTES,
)
@input_error
@mutating
def cmd_tag_remove(args: List[str], storage: Storage) -> str:
    require_args(args, 2, 'Usage: tag-remove "Title" tag')
    note = storage.notes.get_note(args[0])
    if note.remove_tag(args[1]):
        return f"Tag removed from '{args[0]}'."
    return "Tag not found."


@REG.register(
    "delete-note",
    help='Удалить заметку: delete-note "Title"',
    section=SECTION_NOTES,
)
@input_error
@mutating
def cmd_delete_note(args: List[str], storage: Storage) -> str:
    require_args(args, 1, 'Usage: delete-note "Title"')
    if storage.notes.remove(args[0]):
        return f"Deleted note '{args[0]}'."
    return "Note not found."


# ==============================
# Система
# ==============================


@REG.register("hello", help="Привітання від бота", section=SECTION_SYSTEM)
@input_error
def cmd_hello(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    return "Привіт! Чим можу допомогти?"


@REG.register("help", help="Показать справку", section=SECTION_SYSTEM)
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


@REG.register("close", help="Закрыть программу", section=SECTION_SYSTEM)
@REG.register("exit", help="Закрыть программу", section=SECTION_SYSTEM)
@input_error
def cmd_exit(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    return "__EXIT__"


@REG.register("version", help="Показать версию", section=SECTION_SYSTEM)
@input_error
def cmd_version(args: List[str], storage: Storage) -> str:  # noqa: ARG001
    from config import APP_NAME, APP_VERSION
    from storage import STORAGE_FILE

    return f"{APP_NAME} v{APP_VERSION} | data: {STORAGE_FILE}"
