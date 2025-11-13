# Автокомплит команд у CLI

## Загальний огляд

Модуль `cli.py` реалізує інтелектуальну систему автокомплита, яка підказує користувачеві:
- Доступні команди при введенні першого токену
- Імена контактів для команд роботи з адресною книгою
- Назви команд для аргументу команди `help`

Автокомплит побудований на бібліотеці `prompt_toolkit` та працює контекстно-залежно: розуміє, який саме аргумент редагується, та пропонує релевантні підказки.

## Архітектура

### 1. Клас `HintsCompleter`

Кастомний клас, що наслідує `Completer` з `prompt_toolkit`:

```21:68:cli.py
class HintsCompleter(Completer):
    def __init__(self, hints, get_contacts_func=None):
        self.hints = tuple(sorted(set(hints)))
        self.get_contacts_func = get_contacts_func  # optional callback

    def get_completions(self, document, complete_event):
        tb = document.text_before_cursor
        word = document.get_word_before_cursor()
        tokens = tb.split()
        ends_with_space = tb.endswith(" ")

        # 1) Підказки для команди (перший токен)
        if not tokens or (len(tokens) == 1 and not ends_with_space):
            low = word.lower()
            for hint in self.hints:
                if hint.startswith(low):
                    yield Completion(hint, start_position=-len(word))
            return

        # Який токен зараз редагується? (0-based)
        cur_index = len(tokens) if ends_with_space else len(tokens) - 1

        command = tokens[0].lower()
        
        if command == "help" and cur_index == 1:
            low = word.lower()
            for hint in self.hints:
                if hint.startswith(low):
                    yield Completion(hint, start_position=-len(word))
            return
               

        # 2) Підказки імен тільки для ДРУГОГО аргументу (cur_index == 1)
        if cur_index == 1 and command in (
            "add-contact", "change-phone", "show-phone", "add-birthday",
            "show-birthday", "add-email", "delete-email", "add-address",
            "delete-contact", "delete-phone", "delete-address", "find-contact"
        ):
            if self.get_contacts_func:
                low = word.lower()
                for name in self.get_contacts_func():
                    if name.lower().startswith(low):
                        yield Completion(name, start_position=-len(word))
```

**Поля класу:**
- `hints` — кортеж відсортованих назв команд (отриманих з `REG.all_commands()`)
- `get_contacts_func` — колбек-функція для динамічного отримання імен контактів зі сховища

### 2. Метод `get_completions()` — ядро автокомплита

Цей метод викликається `prompt_toolkit` щоразу, коли користувач друкує символ або натискає Tab. Він аналізує поточний стан введення та повертає релевантні підказки.

#### Етап 1: Аналіз контексту

```python
tb = document.text_before_cursor  # весь текст до курсору
word = document.get_word_before_cursor()  # слово під курсором
tokens = tb.split()  # розбиваємо на токени
ends_with_space = tb.endswith(" ")  # чи є пробіл в кінці?
```

**Приклади розбору:**

| Введення | `tb` | `word` | `tokens` | `ends_with_space` |
|----------|------|--------|----------|-------------------|
| `"add│"` | `"add"` | `"add"` | `['add']` | `False` |
| `"add │"` | `"add "` | `""` | `['add']` | `True` |
| `"add Sas│"` | `"add Sas"` | `"Sas"` | `['add','Sas']` | `False` |
| `"add Sasha │"` | `"add Sasha "` | `""` | `['add','Sasha']` | `True` |

#### Етап 2: Автокомплит назви команди

```python
if not tokens or (len(tokens) == 1 and not ends_with_space):
    low = word.lower()
    for hint in self.hints:
        if hint.startswith(low):
            yield Completion(hint, start_position=-len(word))
    return
```

**Коли спрацьовує:**
- Порожній рядок: `"│"`
- Редагується перший токен: `"add│"`, `"sh│"`, `"hel│"`
- НЕ спрацьовує: `"add │"` (є пробіл після команди)

**Приклади:**
```
Введення: "add-"
Результат: add-contact, add-note, add-birthday, add-email, add-address, add-tags

Введення: "sh"
Результат: show-phone, show-birthday

Введення: "del"
Результат: delete-contact, delete-phone, delete-email, delete-address, delete-tag, delete-note
```

#### Етап 3: Визначення поточного токену

```python
cur_index = len(tokens) if ends_with_space else len(tokens) - 1
command = tokens[0].lower()
```

**Логіка визначення індексу:**

| Введення | `tokens` | `ends_with_space` | `cur_index` | Що редагується |
|----------|----------|-------------------|-------------|----------------|
| `"add│"` | `['add']` | `False` | `0` | команда |
| `"add │"` | `['add']` | `True` | `1` | 1-й аргумент |
| `"add Sa│"` | `['add','Sa']` | `False` | `1` | 1-й аргумент |
| `"add Sasha │"` | `['add','Sasha']` | `True` | `2` | 2-й аргумент |
| `"add Sasha 050│"` | `['add','Sasha','050']` | `False` | `2` | 2-й аргумент |

Цей індекс (`cur_index`) показує позицію аргументу, який зараз редагує користувач (0 = команда, 1 = перший аргумент, 2 = другий аргумент тощо).

#### Етап 4: Спеціальний випадок для команди `help`

```python
if command == "help" and cur_index == 1:
    low = word.lower()
    for hint in self.hints:
        if hint.startswith(low):
            yield Completion(hint, start_position=-len(word))
    return
```

**Коли спрацьовує:**
- Команда `help` та редагується перший аргумент

**Приклади:**
```
Введення: "help add-"
Результат: add-contact, add-birthday, add-email, add-address, add-note, add-tags

Введення: "help sh"
Результат: show-phone, show-birthday

Введення: "help │"
Результат: всі доступні команди
```

Це дозволяє користувачеві швидко знайти потрібну команду для перегляду довідки.

#### Етап 5: Автокомплит імен контактів

```python
if cur_index == 1 and command in (
    "add-contact", "change-phone", "show-phone", "add-birthday",
    "show-birthday", "add-email", "delete-email", "add-address",
    "delete-contact", "delete-phone", "delete-address", "find-contact"
):
    if self.get_contacts_func:
        low = word.lower()
        for name in self.get_contacts_func():
            if name.lower().startswith(low):
                yield Completion(name, start_position=-len(word))
```

**Коли спрацьовує:**
- Тільки для **другого токену** (`cur_index == 1`)
- Тільки для команд, що працюють з контактами
- Тільки якщо є функція отримання контактів

**Команди з автокомплітом імен:**
- `add-contact` — додавання контакту (якщо контакт існує, додасть телефон)
- `change-phone` — зміна номера телефону
- `show-phone` — перегляд телефонів
- `add-birthday`, `show-birthday` — робота з днями народження
- `add-email`, `delete-email` — управління email
- `add-address`, `delete-address` — управління адресою
- `delete-contact` — видалення контакту
- `delete-phone` — видалення телефону
- `find-contact` — пошук контакту

**Приклади:**
```
Введення: "show-phone Sa"
Результат: Sasha, Samuel, Sarah (якщо такі контакти є)

Введення: "add-birthday John"
Результат: John, Johnny (якщо такі контакти є)

Введення: "delete-contact │"
Результат: всі імена контактів
```

**Важливо:** Для команд з нотатками (`add-note`, `edit-note`, `delete-note`, `find-note`) автокомплит імен **не працює**, оскільки вони не входять у список команд з контактами.

### 3. Функція `get_contact_names()` — динамічне отримання контактів

```105:144:cli.py
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
```

**Особливості реалізації:**

1. **Універсальність** — підтримує різні реалізації `AddressBook`:
   - Через метод `.all()` (API-based)
   - Через прямий доступ до `.data` або `._data` (dict-based)

2. **Безпека** — обробляє винятки, якщо структура даних відрізняється від очікуваної

3. **Видалення дублікатів** — гарантує, що кожне ім'я з'явиться в списку лише один раз

4. **Динамічність** — список оновлюється при кожному виклику, тому нові контакти відразу з'являються в автокомпліті

### 4. Ініціалізація та підключення

```147:169:cli.py
def run_cli() -> None:
    storage = load_storage()
    # Додано іконку бота після APP_NAME
    print(f"{APP_NAME} {ICON_BOT} v{APP_VERSION}. Type 'help' for commands.")
    print(f"Data stored in: {STORAGE_FILE}\n")

    session = PromptSession()

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
```

**Як працює:**

1. Завантажується сховище (`load_storage()`)
2. Створюється `PromptSession()` з бібліотеки `prompt_toolkit`
3. Створюється `HintsCompleter` з:
   - `hints` — список всіх команд з реєстру (`get_all_commands()`)
   - `get_contacts_func` — лямбда-функція, що викликає `get_contact_names(storage)`
4. У циклі викликається `session.prompt()` з параметрами:
   - `completer=completer` — підключення нашого автокомплітера
   - `complete_while_typing=True` — автокомпліт при друкуванні, не тільки по Tab

**Параметр `complete_while_typing=True`:**
- Підказки з'являються автоматично під час друкування
- Не потрібно натискати Tab для активації
- Користувач бачить доступні варіанти в реальному часі

### 5. Допоміжна функція `get_all_commands()`

```99:101:cli.py
def get_all_commands() -> List[str]:
    """Отримати список всіх доступних команд."""
    return list(REG.all_commands())
```

Проста обгортка, що повертає список всіх зареєстрованих команд з глобального реєстру `REG` (клас `CommandRegistry` з модуля `commands.py`).

## Візуальна схема роботи

```
Користувач друкує → prompt_toolkit викликає get_completions()
                              ↓
                    Аналіз: що редагується?
                    (tokens, cur_index, ends_with_space)
                              ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
    Команда            Аргумент команди        Аргумент "help"
   (cur_index=0)             help              (cur_index=1)
        ↓                (cur_index=1)               ↓
   Фільтр по                 ↓                 Фільтр по
   self.hints           Фільтр по             self.hints
        ↓                self.hints                 ↓
   ["add-contact",           ↓                ["add-contact",
    "help",            ["add-contact",         "show-phone",
    "show-phone",       "show-phone",               ...]
        ...]                 ...]
                              
                      Аргумент контакт-команди
                         (cur_index=1)
                              ↓
                      get_contacts_func()
                              ↓
                      get_contact_names(storage)
                              ↓
                        ["John", "Alice", 
                         "Bob", ...]
                              ↓
                      Completion(name, ...)
```

## Приклади роботи

### Приклад 1: Автокомплит команди

**Введення:**
```
sh│
```

**Результат:**
```
show-phone
show-birthday
```

**Пояснення:** Система знаходить усі команди, що починаються з "sh".

---

### Приклад 2: Автокомплит імені контакту

**Введення:**
```
show-phone J│
```

**Результат (якщо у вас є контакти John, Jane, Jack):**
```
John
Jane
Jack
```

**Пояснення:** Команда `show-phone` входить у список команд з автокомплітом контактів, `cur_index == 1`, тому система викликає `get_contact_names()` та фільтрує імена, що починаються з "J".

---

### Приклад 3: Автокомплит для help

**Введення:**
```
help add-│
```

**Результат:**
```
add-contact
add-birthday
add-email
add-address
add-note
add-tags
```

**Пояснення:** Спеціальний кейс для команди `help` — показує всі команди, що починаються з "add-".

---

### Приклад 4: Автокомплит усіх контактів

**Введення:**
```
delete-contact │
```

**Результат (всі ваші контакти):**
```
Alice
Bob
Charlie
John
Sarah
```

**Пояснення:** Після пробела (`cur_index == 1`) система викликає `get_contact_names()` та показує всі доступні імена.

---

### Приклад 5: Відсутність автокомплиту

**Введення:**
```
add-contact John 050│
```

**Результат:**
```
(нічого)
```

**Пояснення:** Третій аргумент (`cur_index == 2`) не підтримується системою автокомплита — це телефонний номер, який користувач має ввести самостійно.

---

### Приклад 6: Автокомплит для нотаток не працює

**Введення:**
```
edit-note │
```

**Результат:**
```
(нічого)
```

**Пояснення:** Команда `edit-note` не входить у список команд з автокомплітом контактів (рядки 58-62), тому підказки не з'являються. Це потенційне місце для покращення — можна додати автокомплит назв нотаток.

## Переваги реалізації

✅ **Контекстно-залежний** — розуміє, що саме редагується (команда, ім'я контакту, аргумент help)

✅ **Розумний** — різні підказки для різних команд та їх аргументів

✅ **Динамічний** — імена контактів беруться з реального сховища в реальному часі

✅ **Гнучкий** — легко додати нові команди в список (достатньо зареєструвати через `REG.register()`)

✅ **Безпечний** — обробляє помилки та різні структури даних

✅ **Зручний** — працює при друкуванні (`complete_while_typing=True`), не тільки по Tab

✅ **Універсальний** — підтримує різні реалізації `AddressBook`

## Потенційні покращення

1. **Автокомплит назв нотаток** — додати підтримку автокомплита для команд `edit-note`, `delete-note`, `find-note`, `add-tags`, `delete-tag`:
   ```python
   # У HintsCompleter.get_completions()
   if cur_index == 1 and command in (
       "edit-note", "delete-note", "add-tags", "delete-tag"
   ):
       if self.get_notes_func:
           low = word.lower()
           for title in self.get_notes_func():
               if title.lower().startswith(low):
                   yield Completion(title, start_position=-len(word))
   ```

2. **Автокомплит тегів** — для команд `find-tag` та другого аргументу `delete-tag` можна додати автокомплит існуючих тегів

3. **Автокомплит форматів сортування** — для команди `all-notes` можна підказувати `title` або `created`

4. **Fuzzy matching** — замість простого `startswith()` використовувати нечітке співставлення для кращого пошуку

5. **Валідація при автокомпліті** — перевіряти, чи існує контакт/нотатка перед підказкою (для команд типу `change-phone`, `add-birthday`)

## Залежності

Автокомплит вимагає встановлення бібліотеки `prompt_toolkit`:

```bash
pip install prompt_toolkit>=3.0.0
```

Ця залежність вказана в `requirements.txt`:

```
prompt-toolkit>=3.0.0
colorama>=0.4.4
```

## Підсумок

Реалізація автокомплита в `cli.py` — це продуманий та гнучкий підхід до покращення user experience. Система аналізує контекст введення, визначає позицію редагованого аргументу та пропонує релевантні підказки на основі типу команди. Динамічне отримання імен контактів зі сховища робить автокомплит актуальним у реальному часі, а підтримка `complete_while_typing` дозволяє користувачеві бачити підказки безперервно під час друкування.

