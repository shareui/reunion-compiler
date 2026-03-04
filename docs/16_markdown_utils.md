# Markdown Parser

`markdown_utils` позволяет конвертировать текст с Markdown-разметкой в формат который понимает Telegram API — строку без символов разметки и список TLRPC-сущностей с позициями форматирования.

```
import markdown_utils(parse_markdown)
```

---

## Зачем это нужно

Telegram хранит форматирование не как Markdown, а как список объектов — каждый описывает тип, смещение и длину форматированного участка. `parse_markdown` берёт Markdown-строку и возвращает оба компонента уже готовыми к отправке.

---

## Что возвращает `parse_markdown`

`parse_markdown(text)` возвращает объект `ParsedMessage` с двумя полями:

- **`text`** — строка без Markdown-символов (чистый текст)
- **`entities`** — кортеж объектов `RawEntity`

Каждый `RawEntity` содержит:

| Поле | Тип | Описание |
|---|---|---|
| `type` | `TLEntityType` | Тип форматирования (bold, italic, code и др.) |
| `offset` | `int` | Начало форматированного участка в UTF-16 кодовых единицах |
| `length` | `int` | Длина участка в UTF-16 кодовых единицах |
| `language` | `str?` | Только для блоков кода — язык (`"python"`, `"java"` и т.д.) |
| `url` | `str?` | Только для текстовых ссылок — URL |
| `document_id` | `int?` | Только для кастомных эмодзи — ID документа |

Чтобы передать сущности в Telegram API — вызови `.to_tlrpc_object()` на каждой:

```
val parsed = parse_markdown("*жирный* текст")
params.message = parsed.text
params.entities = parsed.entities.map((e) -> e.to_tlrpc_object())
modify params
```

> **Про UTF-16:** Telegram считает смещения и длины в кодовых единицах UTF-16, а не в символах Python. Для ASCII это совпадает, но для кириллицы, эмодзи и некоторых символов — нет. `parse_markdown` делает эту конвертацию автоматически, так что вручную считать не нужно.

---

## Поддерживаемые типы форматирования

| Синтаксис | Что означает |
|---|---|
| `*текст*` | Жирный |
| `_текст_` | Курсив |
| `__текст__` | Подчёркнутый |
| `~текст~` | Зачёркнутый |
| `\|\|текст\|\|` | Спойлер |
| `` `текст` `` | Инлайн-код |
| ```` ```текст``` ```` | Блок кода |
| ```` ```python ... ``` ```` | Блок кода с языком |
| `[текст](https://url.com)` | Текстовая ссылка |
| `[😎](document_id)` | Кастомный эмодзи |

Поддерживается вложенность: например `*жирный и _курсив_ внутри*`.

Специальные символы можно экранировать обратным слешем: `\*не жирный\*` → `*не жирный*`.

---

## Получить ID кастомного эмодзи

ID эмодзи — это числовой идентификатор документа. Получить его можно отправив эмодзи боту [@AdsMarkdownBot](https://t.me/AdsMarkdownBot) в Telegram.

```
[😎](5373141891321699086)   // 😎 с кастомным document_id
```

---

## Примеры

### Простое форматирование

```
import markdown_utils(parse_markdown)
import client_utils(send_message)

fun on_send_message(account, params) {
    if not params.message.startswith(".bold") { default }

    val parsed = parse_markdown("*Это жирный текст*")
    params.message = parsed.text
    params.entities = parsed.entities.map((e) -> e.to_tlrpc_object())
    modify params
}
```

### Блок кода с языком

```
val code = "```python\nprint('Hello!')\n```"
val parsed = parse_markdown(code)
params.message = parsed.text
params.entities = parsed.entities.map((e) -> e.to_tlrpc_object())
modify params
```

### Смешанный контент

```
val text = """
*Погода в $city:*

• Температура: _${temp}°C_
• Состояние: $condition
• Влажность: `${humidity}%`

[Подробнее](https://wttr.in/$city)
"""

val parsed = parse_markdown(text)
params.message = parsed.text
params.entities = parsed.entities.map((e) -> e.to_tlrpc_object())
modify params
```

### Комбинирование с TLRPC вручную

Можно добавить дополнительные сущности поверх тех что вернул `parse_markdown` — например обернуть всё в blockquote:

```
import markdown_utils(parse_markdown)
import org.telegram.tgnet(TLRPC)
import java.util(ArrayList, Arrays)

val parsed = parse_markdown("*список* плагинов")
val tlrcpEnts = parsed.entities.map((e) -> e.to_tlrpc_object())

val blockquote = TLRPC.TL_messageEntityBlockquote()
blockquote.collapsed = true
blockquote.offset = 0
blockquote.length = int(len(parsed.text.encode(encoding="utf_16_le")) / 2)

params.message = parsed.text
params.entities = ArrayList(Arrays.asList([blockquote] + tlrcpEnts))
modify params
```

---

## Важные замечания

**Обработка ошибок.** Если синтаксис Markdown некорректен (незакрытый тег и т.д.) — `parse_markdown` выбросит `SyntaxError`. Оборачивай вызов в `sus/try`:

```
sus {
    val parsed = parse_markdown(text)
    params.message = parsed.text
    params.entities = parsed.entities.map((e) -> e.to_tlrpc_object())
    modify params
} try SyntaxError as e {
    log("Markdown error: ${e.message}")
    params.message = text   // отправляем как обычный текст
    modify params
}
```

**Вложенность.** Базовые комбинации работают (`*жирный и _курсив_*`). Сложная или неоднозначная вложенность может дать неожиданный результат.
