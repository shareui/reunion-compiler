# Хуки на отправку сообщений

Самый частый вид хука для пользовательских плагинов. Срабатывает в момент когда пользователь нажимает «Отправить» — до того как сообщение ушло куда-либо. Можно читать текст, менять его, добавлять форматирование, полностью отменять отправку, или запускать дополнительные действия.

---

## Регистрация

```
plugin MyPlugin {
    fun on_load() {
        hook_send_message
    }

    fun on_send_message(account, params) {
        // твой код
    }
}
```

`hook_send_message` в `on_load` — регистрирует перехватчик. Без этой строки `on_send_message` никогда не вызовется.

---

## Объект `params`

`params` — это объект с данными об отправляемом сообщении.

| Поле | Тип | Описание |
|---|---|---|
| `params.message` | `str` | Текст сообщения. Можно читать и менять |
| `params.peer` | `int` | ID чата/пользователя куда отправляется |
| `params.entities` | список | TLRPC-сущности форматирования (жирный, курсив, ссылки и т.д.) |

Чаще всего работаешь с `params.message`. Остальные поля нужны для более сложных сценариев — например добавления форматирования через TLRPC напрямую.

---

## Терминаторы

| Что написать | Что произойдёт |
|---|---|
| `default` | Сообщение отправляется как есть |
| `modify params` | Сообщение отправляется с изменёнными `params` |
| `cancel` | Сообщение не отправляется |

**Важно:** если ты изменил `params.message` но написал `default` вместо `modify params` — изменения не применятся. Нужно явно сказать `modify params`.

---

## Базовые паттерны

### Проверка команды и пропуск остального

Самый частый паттерн — плагин реагирует только на определённую команду, всё остальное пропускает:

```
fun on_send_message(account, params) {
    if not params.message {
        default
    }

    if not params.message.startswith(".mycommand") {
        default
    }

    // дальше — обработка команды
    cancel
}
```

### Изменение текста

```
fun on_send_message(account, params) {
    if not params.message {
        default
    }

    val modified = params.message.replace("https://", "")
    if modified != params.message {
        params.message = modified
        modify params
    }

    default
}
```

### Отмена с уведомлением

```
fun on_send_message(account, params) {
    if not params.message {
        default
    }

    if params.message.startswith(".spam") {
        BulletinHelper.show_info("Spam command disabled")
        cancel
    }

    default
}
```

---

## Тяжёлые операции — фоновый поток

Если нужно сделать что-то медленное (сетевой запрос, сложные вычисления) — нельзя делать это прямо в `on_send_message`, потому что он вызывается на UI-потоке. Зависание UI-потока заморозит интерфейс.

Правильный паттерн — отменить исходное сообщение, сделать работу в фоне, и отправить результат через `send_message`:

```
import client_utils(send_message, run_on_queue, get_last_fragment)
import android_utils(run_on_ui_thread)
import ui.bulletin(BulletinHelper)

fun on_send_message(account, params) {
    if not params.message {
        default
    }
    if not params.message.startswith(".wt") {
        default
    }

    val parts = params.message.strip().split(" ", 1)
    val city = if parts.length > 1 then parts[1].strip() else "Moscow"
    val peer = params.peer

    // запускаем тяжёлую работу в фоне
    run_on_queue(() ->
        sus {
            val data = fetchWeatherData(city)
            val text = if data != null then formatWeatherData(data, city) else "Failed to fetch weather"
            // возвращаемся на UI-поток чтобы отправить сообщение
            run_on_ui_thread(() ->
                send_message(peer, text)
            )
        } try e {
            run_on_ui_thread(() ->
                send_message(peer, "Error: ${e.message}")
            )
        }
    )

    cancel   // отменяем исходное ".wt Moscow" — вместо него придёт результат
}
```

---

## Форматирование через `markdown_utils`

Если нужно отправить текст с форматированием (жирный, курсив, ссылки, кодовые блоки) — используй `parse_markdown`:

```
import markdown_utils(parse_markdown)

fun on_send_message(account, params) {
    if not params.message.startswith(".bold") {
        default
    }

    val text = "*Это жирный текст*"
    val parsed = parse_markdown(text)
    params.message = parsed.message
    params.entities = parsed.entities
    modify params
}
```

`parse_markdown` принимает строку с Markdown и возвращает объект с двумя полями:
- `message` — текст без Markdown-символов
- `entities` — список TLRPC-сущностей с позициями и типами форматирования

---

## Форматирование через TLRPC напрямую

Для более тонкого контроля — можно работать с TLRPC-сущностями вручную. Например, добавить цитату (`blockquote`):

```
import org.telegram.tgnet(TLRPC)
import java.util(ArrayList, Arrays)

fun on_send_message(account, params) {
    // ... формируем params.message ...

    val blockquote = TLRPC.TL_messageEntityBlockquote()
    blockquote.collapsed = true
    blockquote.offset = 0
    // длина в кодовых единицах UTF-16 (так считает Telegram)
    blockquote.length = int(len(params.message.encode(encoding="utf_16_le")) / 2)

    params.entities = ArrayList(Arrays.asList([blockquote]))
    modify params
}
```

Telegram считает смещения и длины в кодовых единицах UTF-16, а не в символах Python. Поэтому для русского текста и эмодзи длина может отличаться от `len(text)`. Правильно: `int(len(text.encode("utf_16_le")) / 2)`.

---

## Полный пример: Weather Plugin

```
metainfo {
    id: "weather"
    name: "Weather"
    version: "1.0.0"
    author: "you"
    description: "Current weather [.wt city]"
    min_version: "11.12.0"
    requirements: "requests"
}

import base_plugin(BasePlugin, HookResult, HookStrategy)
import client_utils(send_message, run_on_queue)
import android_utils(run_on_ui_thread, log)
import requests

fun fetchWeatherData(city) {
    sus {
        val url = "https://wttr.in/${city}?format=j1"
        val response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if response.status_code != 200 {
            return null
        }
        return response.json()
    } try e {
        log("Weather API error: ${e.message}")
        return null
    }
}

fun formatWeatherData(data, city) {
    sus {
        val area = data.get("nearest_area", [{}])[0]
        val cityName = area.get("areaName", [{}])[0].get("value", city)
        val country = area.get("country", [{}])[0].get("value", "")
        val current = data.get("current_condition", [{}])[0]
        val temp = current.get("temp_C", "N/A")
        val feels = current.get("FeelsLikeC", "N/A")
        val condition = current.get("weatherDesc", [{}])[0].get("value", "Unknown")
        val humidity = current.get("humidity", "N/A")
        val wind = current.get("windspeedKmph", "N/A")
        return "Weather in $cityName, $country:\n\n• Temp: ${temp}°C (feels like ${feels}°C)\n• ${condition}\n• Humidity: ${humidity}%\n• Wind: ${wind} km/h"
    } try e {
        return "Error formatting weather data"
    }
}

plugin WeatherPlugin {
    fun on_load() {
        hook_send_message
    }

    fun on_send_message(account, params) {
        if not params.message {
            default
        }
        if not params.message.startswith(".wt") {
            default
        }

        val parts = params.message.strip().split(" ", 1)
        val city = if parts.length > 1 then parts[1].strip() else "Moscow"
        val peer = params.peer

        run_on_queue(() ->
            sus {
                val data = fetchWeatherData(city)
                val text = if data != null
                    then formatWeatherData(data, city)
                    else "Failed to fetch weather for '$city'"
                run_on_ui_thread(() ->
                    send_message(peer, text)
                )
            } try e {
                run_on_ui_thread(() ->
                    send_message(peer, "Error: ${e.message}")
                )
            }
        )

        cancel
    }
}
```

---

## Типичные ошибки

**Изменил `params.message` но сообщение ушло без изменений.** Написал `default` вместо `modify params`.

**Плагин не реагирует на команду.** Забыл `hook_send_message` в `on_load`.

**Приложение зависает при отправке.** Делаешь сетевой запрос прямо в `on_send_message` без `run_on_queue`.

**`params.message` не является строкой.** В некоторых типах сообщений (стикеры, медиа без текста) `params.message` может быть `null` или не строкой. Всегда проверяй в начале:

```
if not params.message {
    default
}
```
