"""
Модель даних для контактів та нотаток
"""

from __future__ import annotations

from collections import UserDict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import re
from calendar import isleap  # === ДОДАНО ===

from config import (
    BIRTHDAY_FORMAT,
    EMAIL_REGEX,
    PHONE_DIGITS,
    PHONE_REGEX,
)


# ==============================
# Поля для контактів (валідація)
# ==============================


class Field:
    """Базове поле з рядковим значенням."""

    def __init__(self, value: str) -> None:
        self._value = None
        self.value = value  # викликає setter

    @property
    def value(self) -> str:
        if self._value is None:
            return ""
        return self._value

    @value.setter
    def value(self, new_value: str) -> None:
        self._value = (
            new_value.strip() if isinstance(new_value, str) else str(new_value)
        )

    def __str__(self) -> str:
        return self.value


class Name(Field):
    """Ім'я контакта."""

    pass


class Phone(Field):
    """Телефон: рівно 10 цифр."""

    _re = re.compile(PHONE_REGEX)

    @Field.value.setter  # type: ignore[attr-defined]
    def value(self, new_value: str) -> None:
        s = (new_value or "").strip()
        if not self._re.fullmatch(s):
            raise ValueError(f"Phone must contain exactly {PHONE_DIGITS} digits.")
        self._value = s


class Email(Field):
    """Email з базовою валідацією."""

    _re = re.compile(EMAIL_REGEX)

    @Field.value.setter  # type: ignore[attr-defined]
    def value(self, new_value: str) -> None:
        s = (new_value or "").strip()
        if not self._re.fullmatch(s):
            raise ValueError("Invalid email format.")
        self._value = s


class Address(Field):
    """Адреса контакта."""

    pass


class Birthday(Field):
    """Дата народження у форматі DD.MM.YYYY."""

    @Field.value.setter  # type: ignore[attr-defined]
    def value(self, new_value: str) -> None:
        s = (new_value or "").strip()
        try:
            dt = datetime.strptime(s, BIRTHDAY_FORMAT)
        except ValueError:
            raise ValueError(f"Birthday must be in {BIRTHDAY_FORMAT} format.")
        self._value = dt.strftime(BIRTHDAY_FORMAT)

    def as_date(self) -> date:
        """Перетворити на об'єкт date."""
        return datetime.strptime(self.value, BIRTHDAY_FORMAT).date()


# ==============================
# Контакт та Книга контактів
# ==============================


class Record:
    """
    Один контакт з полями та методами управління.

    Приклад:
        rec = Record(Name("John Doe"))
        rec.add_phone(Phone("1234567890"))
        rec.add_email(Email("john@example.com"))
        rec.set_birthday(Birthday("15.03.1990"))
        rec.set_address(Address("Kyiv, Ukraine"))

        print(rec)
        # Output: Name: John Doe | Phones: 1234567890 | Emails: john@example.com |
        #         Address: Kyiv, Ukraine | Birthday: 15.03.1990

        print(rec.days_to_birthday())  # кількість днів до ДН
    """

    def __init__(self, name: Name) -> None:
        self.name: Name = name
        self.phones: List[Phone] = []
        self.emails: List[Email] = []
        self.address: Optional[Address] = None
        self.birthday: Optional[Birthday] = None

    # ----- Телефони -----
    def add_phone(self, phone: Phone) -> None:
        """Додати номер телефону."""
        if phone.value not in [p.value for p in self.phones]:
            self.phones.append(phone)

    def remove_phone(self, phone_value: str) -> bool:
        """Видалити номер телефону за значенням."""
        for i, p in enumerate(self.phones):
            if p.value == phone_value:
                self.phones.pop(i)
                return True
        return False

    def edit_phone(self, old_value: str, new_value: str) -> None:
        """Змінити номер телефону."""
        for p in self.phones:
            if p.value == old_value:
                p.value = new_value  # викликає валідацію
                return
        raise KeyError(f"Phone '{old_value}' not found for contact '{self.name}'.")

    # ----- Email -----
    def add_email(self, email: Email) -> None:
        """Додати email."""
        if email.value not in [e.value for e in self.emails]:
            self.emails.append(email)

    def remove_email(self, email_value: str) -> bool:
        """Видалити email за значенням."""
        for i, e in enumerate(self.emails):
            if e.value == email_value:
                self.emails.pop(i)
                return True
        return False

    # ----- Адреса -----
    def set_address(self, address: Address) -> None:
        """Встановити адресу."""
        self.address = address

    def remove_address(self) -> bool:
        """Видалити адресу."""
        if self.address:
            self.address = None
            return True
        return False

    # ----- День народження -----
    def set_birthday(self, bday: Birthday) -> None:
        """Встановити день народження."""
        self.birthday = bday

    def days_to_birthday(self, today: Optional[date] = None) -> Optional[int]:
        """
        Кількість днів до найближчого дня народження.

        Використовує get_next_birthday(), яка коректно обробляє
        випадок 29 лютого у невисокосні роки (зсув на 1 березня).
        """
        if not self.birthday:
            return None
        today = today or date.today()
        next_bd = self.get_next_birthday(today)
        if not next_bd:
            return None
        return (next_bd - today).days


    def get_next_birthday(self, today: Optional[date] = None) -> Optional[date]:
        """
        Отримати дату наступного дня народження.

        Аналогічно до days_to_birthday(), але повертає саму дату замість кількості днів.

        Приклади:
        - Сьогодні 10.11, день народження 15.11 → date(2025, 11, 15)
        - Сьогодні 20.11, день народження 15.11 → date(2026, 11, 15)
        """
        if not self.birthday:
            return None

        today = today or date.today()
        born = self.birthday.as_date()

        # === Обробка високосного року для 29 лютого ===
        year = today.year
        month = born.month
        day = born.day
        if month == 2 and day == 29 and not isleap(year):
            day = 1
            month = 3

        next_bd = date(year, month, day)

        if next_bd < today:
            year += 1
            month = born.month
            day = born.day
            if month == 2 and day == 29 and not isleap(year):
                day = 1
                month = 3
            next_bd = date(year, month, day)

        # === Кінець додавання ===
        return next_bd


    def __str__(self) -> str:
        parts = [f"Name: {self.name}"]
        if self.phones:
            parts.append("Phones: " + ", ".join(p.value for p in self.phones))
        if self.emails:
            parts.append("Emails: " + ", ".join(e.value for e in self.emails))
        if self.address:
            parts.append(f"Address: {self.address}")
        if self.birthday:
            parts.append(f"Birthday: {self.birthday.value}")
        return " | ".join(parts)


class AddressBook(UserDict):
    """Книга контактів (ім'я → Record)."""

    def add_record(self, record: Record) -> None:
        """Додати контакт."""
        key = record.name.value.lower()
        if key in self.data:
            raise KeyError(f"Contact '{record.name.value}' already exists.")
        self.data[key] = record

    def get_record(self, name: str) -> Record:
        """Отримати контакт за іменем."""
        key = name.strip().lower()
        if key not in self.data:
            raise KeyError(name)
        return self.data[key]

    def remove_record(self, name: str) -> bool:
        """Видалити контакт за іменем."""
        key = name.strip().lower()
        return self.data.pop(key, None) is not None

    def search(self, query: str) -> List[Record]:
        """Пошук контактів за різними полями."""
        q = query.lower().strip()
        results: List[Record] = []
        for r in self.data.values():
            hay = [
                r.name.value.lower(),
                *(p.value for p in r.phones),
                *(e.value.lower() for e in r.emails),
                (r.address.value.lower() if r.address else ""),
                (r.birthday.value if r.birthday else ""),
            ]
            if any(q in h.lower() for h in hay if h):
                results.append(r)
        return results

    def all(self) -> List[Record]:
        """Отримати всі контакти, відсортовані за іменем."""
        return sorted(self.data.values(), key=lambda r: r.name.value.lower())

    def upcoming_birthdays(
        self, days: int, today: Optional[date] = None
    ) -> Dict[int, List[Tuple[str, str, str]]]:
        """
        Контакти з днями народження протягом наступних N днів.
        Повертає: дні_до → список (ім'я, dd.mm.yyyy, день_тижня)
        """
        today = today or date.today()
        bucket: Dict[int, List[Tuple[str, str, str]]] = {}

        for r in self.data.values():
            delta = r.days_to_birthday(today)
            if delta is None or not (0 <= delta <= days):
                continue

            next_bd = r.get_next_birthday(today)
            wk = next_bd.strftime("%A")
            bucket.setdefault(delta, []).append((r.name.value, r.birthday.value, wk))

        # Сортуємо кожен список за іменем
        for d in bucket:
            bucket[d].sort(key=lambda t: t[0].lower())

        return dict(sorted(bucket.items(), key=lambda kv: kv[0]))


# ==============================
# Нотатки
# ==============================


@dataclass
class Note:
    """Нотатка з текстом та тегами."""

    title: str
    text: str
    tags: set[str] = field(default_factory=set)
    created: datetime = field(default_factory=datetime.now)

    def add_tags(self, *tags: str) -> None:
        """Додати теги до нотатки."""
        self.tags.update(t.strip().lower() for t in tags if t.strip())

    def remove_tag(self, tag: str) -> bool:
        """Видалити тег з нотатки."""
        t = tag.strip().lower()
        if t in self.tags:
            self.tags.remove(t)
            return True
        return False


class NoteBook(UserDict):
    """Записна книжка (назва → Note)."""

    def add(self, note: Note) -> None:
        """Додати нотатку."""
        key = note.title.strip().lower()
        if key in self.data:
            raise KeyError(f"Note '{note.title}' already exists.")
        self.data[key] = note

    def get_note(self, title: str) -> Note:
        """Отримати нотатку за назвою."""
        key = title.strip().lower()
        if key not in self.data:
            raise KeyError(title)
        return self.data[key]

    def remove(self, title: str) -> bool:
        """Видалити нотатку за назвою."""
        key = title.strip().lower()
        return self.data.pop(key, None) is not None

    def search_text(self, query: str) -> List[Note]:
        """Пошук нотаток за текстом та назвою."""
        q = query.lower().strip()
        return [
            n for n in self.data.values() if q in n.text.lower() or q in n.title.lower()
        ]

    def search_tag(self, tag: str) -> List[Note]:
        """Пошук нотаток за тегом."""
        t = tag.lower().strip()
        return [n for n in self.data.values() if t in n.tags]

    def all(self, sort_by: str = "title") -> List[Note]:
        """Отримати всі нотатки з сортуванням."""
        if sort_by == "created":
            return sorted(self.data.values(), key=lambda n: n.created)
        return sorted(self.data.values(), key=lambda n: n.title.lower())
 
 