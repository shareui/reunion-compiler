# Настройки плагина

Блок `settings` описывает экран настроек плагина в приложении. Пользователь открывает его через список плагинов — и видит контролы которые ты задал. Компилятор превращает блок в метод `create_settings()`.

Настройки не требуют знания Xposed или Java — это чистый Reunion-синтаксис. Подробнее о всех возможностях настроек — на странице документации exteraGram: [https://plugins.exteragram.app/docs/plugin-settings](https://plugins.exteragram.app/docs/plugin-settings).

---

## Базовый пример

```
settings {
    header "General"

    switch "dont_send_typing" {
        text: "Don't send typing status"
        default: true
        subtext: "Prevents sending typing indicators to other users"
        icon: "msg_typing"
    }

    divider

    header "Advanced"

    input "custom_prefix" {
        text: "Message prefix"
        default: ""
    }
}
```

---

## Чтение значений в коде

Обратиться к значению настройки из любого метода внутри `plugin`:

```
val enabled = setting("dont_send_typing")           // без дефолта
val prefix = setting("custom_prefix", "")           // с дефолтом
val count = setting("max_count", 10)
```

Если пользователь ещё не открывал настройки — вернётся дефолт из `setting(key, default)` или `null` если дефолт не задан.

---

## Все контролы

### `switch` — переключатель

```
switch "key" {
    text: "Название переключателя"
    default: true
    subtext: "Подсказка под названием"
    icon: "msg_typing"
    on_change: (val) -> log("changed: $val")
}
```

| Поле | Обязательное | Описание |
|---|---|---|
| `text` | ✅ | Название |
| `default` | ✅ | `true` или `false` |
| `subtext` | — | Серый текст под названием |
| `icon` | — | Иконка слева |
| `on_change` | — | Колбэк при изменении, получает новое `bool` значение |

**Получение значения:**
```
val enabled = setting("key", true)   // вернёт bool
if setting("key", true) {
    // включено
}
```

---

### `input` — однострочное текстовое поле

```
input "key" {
    text: "Команда"
    default: ".wt"
    subtext: "Команда для получения погоды"
    icon: "msg_text"
    on_change: (val) -> log("new value: $val")
}
```

| Поле | Обязательное | Описание |
|---|---|---|
| `text` | ✅ | Название поля |
| `default` | ✅ | Значение по умолчанию |
| `subtext` | — | Подсказка |
| `icon` | — | Иконка слева |
| `on_change` | — | Колбэк при изменении, получает новую строку |

**Получение значения:**
```
val cmd = setting("key", ".wt")   // вернёт str
if params.message.startswith(setting("key", ".wt")) {
    // ...
}
```

---

### `selector` — выбор из списка

```
selector "theme" {
    text: "Тема"
    default: 0
    items: ["Авто", "Светлая", "Тёмная"]
    icon: "msg_theme"
    on_change: (idx) -> log("selected: $idx")
}
```

| Поле | Обязательное | Описание |
|---|---|---|
| `text` | ✅ | Название |
| `default` | ✅ | Индекс выбранного элемента по умолчанию (с нуля) |
| `items` | ✅ | Список строк |
| `icon` | — | Иконка слева |
| `on_change` | — | Колбэк при изменении, получает индекс `int` |

**Получение значения:**

`setting("theme")` вернёт **индекс** выбранного элемента, не строку. Чтобы получить строку:
```
val idx = setting("theme", 0)           // вернёт int: 0, 1 или 2
val themes = ["Авто", "Светлая", "Тёмная"]
val themeName = themes[idx]             // вернёт str
```

---

### `edit_text` — многострочное поле

```
edit_text "notes" {
    hint: "Введите текст..."
    default: ""
    multiline: true
    max_length: 1000
}
```

| Поле | Обязательное | Описание |
|---|---|---|
| `hint` | ✅ | Placeholder когда поле пустое |
| `default` | ✅ | Значение по умолчанию |
| `multiline` | — | `true` чтобы разрешить переносы строк |
| `max_length` | — | Максимальное количество символов |

**Получение значения:**
```
val notes = setting("notes", "")   // вернёт str, возможно многострочный
val lines = notes.split("\n")
```

---

### `header` — заголовок секции

```
header "Основные настройки"
```

Только текст, без дополнительных полей. Значение не хранит — `setting()` не нужен.

---

### `divider` — разделитель

```
divider                 // просто линия
divider "Ссылки"        // линия с текстом
```

Визуальный элемент, значение не хранит.

---

### `text` — кликабельный элемент

```
text "Открыть документацию" {
    icon: "msg_arrow_forward"
    on_click: (view) -> log("clicked")
}
```

| Поле | Обязательное | Описание |
|---|---|---|
| `icon` | — | Иконка слева |
| `on_click` | — | Колбэк при нажатии, получает `view` |

Значение не хранит — используется только для действий при нажатии.

---

## Иконки

Иконки задаются строковым именем, например `"msg_typing"`, `"msg_text"`, `"msg_theme"`. Это внутренние ресурсы приложения — их список нигде не задокументирован официально.

Чтобы найти нужную иконку — используй плагин **DevSettingsIcon**: [https://t.me/CactusPlugins/8](https://t.me/CactusPlugins/8). Он отображает все доступные иконки прямо внутри приложения с их именами.

---

## Колбэки `on_change`

Колбэки — лямбды которые вызываются когда пользователь меняет значение настройки. Можно использовать для немедленной реакции — например обновить кэшированное значение:

```
switch "feature_enabled" {
    text: "Enable feature"
    default: false
    on_change: (val) -> {
        if val {
            log("Feature enabled")
        } else {
            log("Feature disabled")
        }
    }
}
```

Колбэки вызываются на UI-потоке. Если нужно сделать что-то тяжёлое — используй `run_on_queue`.

---

## Полный пример

```
settings {
    header "Команды"

    input "plf_cmd" {
        text: "Команда отправки плагина"
        default: ".plf"
        icon: "msg_text"
    }

    input "chelp_cmd" {
        text: "Команда списка плагинов"
        default: ".chelp"
        icon: "msg_text"
    }

    divider

    header "Внешний вид"

    selector "list_style" {
        text: "Стиль списка"
        default: 0
        items: ["Компактный", "Подробный"]
        icon: "msg_list"
    }

    switch "show_versions" {
        text: "Показывать версии"
        default: true
        subtext: "Отображать номер версии рядом с именем плагина"
        icon: "msg_info"
    }

    divider

    header "Эмодзи статуса"

    input "emoji_enabled" {
        text: "ID эмодзи (включён)"
        default: "5776375003280838798"
    }

    input "emoji_disabled" {
        text: "ID эмодзи (выключен)"
        default: "5778527486270770928"
    }
}
```
