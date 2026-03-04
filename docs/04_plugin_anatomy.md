# Анатомия плагина

В этом разделе разберём из чего состоит плагин и как всё работает вместе. В качестве примера — **CactusLib Mini**: плагин с командами для работы с другими плагинами.

---

## Структура файла `.reu`

Файл плагина состоит из четырёх блоков. Все опциональны кроме `plugin`, но обычно нужны все:

```
metainfo { ... }     // описание плагина
import ...           // подключение библиотек
plugin Name { ... }  // код плагина
settings { ... }     // настройки UI
```

---

## Блок `metainfo`

Паспорт плагина. Читается приложением при установке и отображается в списке плагинов.

```
metainfo {
    id: "shareui_clibmini"
    name: "CactusLib Mini"
    version: "1.0.1"
    author: "@CactusPlugins | fork by @shareui(@doctashare)"
    description: "Mini version of CactusLib :D\n\nFork supports premium emojis"
    min_version: "12.2.10"
}
```

### Все поля

| Поле | Обязательное | Описание |
|---|---|---|
| `id` | ✅ | Уникальный идентификатор. По нему приложение отличает плагины. Только латиница, цифры, подчёркивание |
| `name` | ✅ | Отображаемое название |
| `version` | ✅ | Версия в формате `1.0.0` |
| `author` | ✅ | Автор |
| `description` | ✅ | Описание. Поддерживает `\n` для переносов строк |
| `min_version` | — | Минимальная версия exteraGram. Если у пользователя старее — плагин не установится |
| `icon` | — | Иконка плагина в формате `"plugin232/1"` |
| `requirements` | — | Python-библиотеки через запятую: `"requests, mpmath"`. Только pure-Python библиотеки — без нативного кода |

> **Про `id`**: если ты публикуешь плагин — добавляй к нему свой никнейм, например `myname_pluginname`. Это избавляет от конфликтов когда два автора называют плагины одинаково.

---

## Импорты

После `metainfo` — импорты всего что нужно:

```
import base_plugin(BasePlugin, HookResult, HookStrategy)
import client_utils
import android_utils(log)
import markdown_utils(parse_markdown)
import ui.bulletin(BulletinHelper)
import ui.settings(Input)
import pathlib
import com.exteragram.messenger.plugins(PluginsController)
import org.telegram.messenger(ApplicationLoader, FileLoader)
import java.io(File)
import java.util(ArrayList, Arrays)
import org.telegram.tgnet(TLRPC)
```

Первая строка — **обязательна** в каждом плагине. Она подключает базовый класс и типы результатов хуков.

Остальное — по необходимости. Компилятор сам добавит нужные системные импорты, но пользовательские нужно указывать явно.

### Что откуда импортировать

| Что нужно | Откуда |
|---|---|
| Базовый класс плагина | `base_plugin` |
| `log()` | `android_utils` |
| Отправка сообщений/медиа | `client_utils` |
| Всплывающие уведомления | `ui.bulletin` |
| Диалоги | `ui.alert` |
| Контролы настроек | `ui.settings` |
| Поиск Java-классов | `hook_utils` |
| Markdown в тексте | `markdown_utils` |
| Java-типы | `java.lang`, `java.util`, `java.io` |
| Классы Telegram | `org.telegram.*` |
| Классы Android | `android.*` |
| Классы exteraGram | `com.exteragram.*` |

---

## Блок `plugin`

Это сам плагин. Всё поведение — здесь.

```
plugin CactusLibMini {
    hook_send_message

    fun on_load() {
        hook_send_message
        val plfCmd = setting("plf_cmd", ".plf")
        val chelpCmd = setting("chelp_cmd", ".chelp")
    }

    fun on_send_message(account, params) {
        // обработчик исходящих сообщений
    }
}
```

Компилятор превращает `plugin CactusLibMini { }` в `class CactusLibMini(BasePlugin): `.

### Жизненный цикл: `on_load` и `on_unload`

```
fun on_load() {
    // вызывается при включении плагина или запуске приложения
    // здесь регистрируем хуки, инициализируем состояние
    hook_send_message
    hook "TL_messages_setTyping"
}

fun on_unload() {
    // вызывается при отключении плагина
    // здесь освобождаем ресурсы, если нужно
    log("Plugin stopped")
}
```

`on_load` — точка входа. Без регистрации хуков здесь никакой перехват работать не будет.

### Регистрация хуков

Внутри `on_load` говоришь приложению что именно перехватывать:

```
fun on_load() {
    hook_send_message                       // перехват исходящих сообщений
    hook "TL_messages_setTyping"            // перехват TL-запроса
    hook "TL_account_updateStatus"          // ещё один TL-запрос
}
```

Подробнее о том что такое хуки и зачем они нужны — в разделе [Как работают хуки](https://github.com/shareui/reunion-compiler/tree/main/docs/05_how_hooks_work.md).

---

## Доступ к настройкам

Обратиться к значению настройки из любого места внутри `plugin`:

```
val cmd = setting("plf_cmd", ".plf")       // с дефолтом
val cmd = setting("plf_cmd")               // без дефолта
```

Компилятор разворачивает это в `self.get_setting("plf_cmd", ".plf")`.

---

## Логирование

```
log("Plugin loaded")
log("Error: ${e.message}")
```

Превращается в `self.log(...)`. Логи видны в режиме отладки через `extera first_plugin.plugin --debug`.

---

## Блок `settings`

Декларация UI настроек. Компилятор генерирует метод `create_settings()` который приложение вызывает для отображения экрана настроек плагина.

```
settings {
    input "plf_cmd" {
        text: "Send plugin file command"
        default: ".plf"
    }

    input "chelp_cmd" {
        text: "Send command help command"
        default: ".chelp"
    }

    input "emoji_enabled" {
        text: "Enabled emoji ID"
        default: "5776375003280838798"
    }

    input "emoji_disabled" {
        text: "Disabled emoji ID"
        default: "5778527486270770928"
    }
}
```

### Все доступные контролы

**`switch`** — переключатель вкл/выкл:
```
switch "dont_send_typing" {
    text: "Don't send typing status"
    default: true
    subtext: "Prevents sending typing indicators"
    icon: "msg_typing"
    on_change: (val) -> log("changed: $val")
}
```

**`input`** — однострочное текстовое поле:
```
input "custom_prefix" {
    text: "Message prefix"
    default: ""
    subtext: "Prepend this to every sent message"
    icon: "msg_text"
    on_change: (val) -> log("prefix: $val")
}
```

**`selector`** — выбор из списка:
```
selector "theme" {
    text: "Theme"
    default: 0
    items: ["Auto", "Light", "Dark"]
    icon: "msg_theme"
    on_change: (idx) -> log("theme: $idx")
}
```

**`edit_text`** — многострочное текстовое поле:
```
edit_text "notes" {
    hint: "Enter notes..."
    default: ""
    multiline: true
    max_length: 1000
}
```

**`header`** — заголовок секции:
```
header "General"
```

**`divider`** — разделитель (с текстом или без):
```
divider
divider "Links"
```

**`text`** — кликабельный текст (для навигации или действий):
```
text "Open documentation" {
    icon: "msg_arrow_forward"
    on_click: (view) -> log("clicked")
}
```

---

## Полный пример — CactusLib Mini

Разберём как всё работает вместе на реальном плагине. Он умеет две команды:
- `.plf <plugin_id>` — отправляет `.plugin` файл указанного плагина в чат
- `.chelp` — выводит список всех установленных плагинов с их статусом

```
metainfo {
    id: "shareui_clibmini"
    name: "CactusLib Mini"
    version: "1.0.1"
    author: "@CactusPlugins | fork by @shareui(@doctashare)"
    description: "Mini version of CactusLib :D\n\nThe fork now supports premium emojis"
    min_version: "12.2.10"
}

import base_plugin(BasePlugin, HookResult, HookStrategy)
import client_utils
import android_utils(log)
import markdown_utils(parse_markdown)
import ui.bulletin(BulletinHelper)
import ui.settings(Input)
import pathlib
import com.exteragram.messenger.plugins(PluginsController)
import org.telegram.messenger(ApplicationLoader)
import java.io(File)
import java.util(ArrayList, Arrays)
import org.telegram.tgnet(TLRPC)

// вспомогательная функция вне плагина — обычная fun на верхнем уровне
fun getPythonEngine() {
    sus {
        val controller = PluginsController.getInstance()
        if not controller { return null }
        val engines = getattr(controller, "engines", null)
        if not engines { return null }
        return engines.get("python")
    } try {
        return null
    }
}

plugin CactusLibMini {
    hook_send_message       // объявляем что будем перехватывать сообщения

    fun on_load() {
        hook_send_message   // регистрируем хук
        // читаем настройки при старте (кэшируем значения)
        val plfCmd = setting("plf_cmd", ".plf")
        val chelpCmd = setting("chelp_cmd", ".chelp")
    }

    fun on_send_message(account, params) {
        // params.message — текст сообщения который пользователь собирается отправить
        if not params.message {
            default   // пустое сообщение — пропускаем
        }

        val msg = params.message.strip()
        val plfCmd = setting("plf_cmd", ".plf")
        val chelpCmd = setting("chelp_cmd", ".chelp")

        // --- команда .plf ---
        if msg.startswith(plfCmd) {
            if len(msg.split()) != 2 {
                BulletinHelper.show_info("Usage: $plfCmd <plugin_id>")
                cancel   // отменяем отправку, показываем подсказку
            }

            val pluginId = msg.split()[1]
            sus {
                val plp = PluginsController.getInstance().getPluginPath(pluginId)
                if not plp or not pathlib.Path(plp).exists() {
                    BulletinHelper.show_info("Plugin not found: $pluginId")
                    cancel
                }

                val pl = PluginsController.getInstance().plugins.get(pluginId)
                val pluginVersion = pl.getVersion() or "1.0.0"
                val pluginName = pl.getName()

                // создаём временный файл через Java File API
                val dir = File(ApplicationLoader.applicationContext.getExternalCacheDir(), "cactuslib_temp")
                if not dir.exists() { dir.mkdirs() }
                val file = File(dir, "${pluginId}-${pluginVersion}.plugin")

                sus {
                    val srcData = open(plp, "rb").read()
                    open(file.getAbsolutePath(), "wb").write(srcData)
                } try e {
                    log("file copy failed: ${e}")
                    cancel
                }

                client_utils.send_document(params.peer, file.getAbsolutePath(), pluginName)
                cancel   // отменяем исходное сообщение — вместо него уже ушёл файл
            } try e {
                BulletinHelper.show_info("Error while sending plugin file")
                log("${e}")
                cancel
            }
        }

        // --- команда .chelp ---
        if msg.startswith(chelpCmd) {
            sus {
                val emojiEnabled = setting("emoji_enabled", "5776375003280838798")
                val emojiDisabled = setting("emoji_disabled", "5778527486270770928")
                val pls = PluginsController.getInstance().plugins

                var plugins = []
                var enabled = 0
                var disabled = 0

                // итерируем по Java Map через keySet/values
                for pluginId, pl in zip(list(pls.keySet().toArray()), list(pls.values().toArray())) {
                    val isEnabled = pl.isEnabled()
                    var state = "[❌]($emojiDisabled)"
                    if isEnabled {
                        state = "[✅]($emojiEnabled)"
                        enabled = enabled + 1
                    }
                    if not isEnabled { disabled = disabled + 1 }
                    plugins.append("[${pl.getVersion() or '-'}] $state *${pl.getName()}* (`$pluginId`)")
                }

                plugins.append("\n${len(plugins)} plugins, $enabled enabled, $disabled disabled.")

                // parse_markdown конвертирует markdown-текст в TLRPC-сущности
                val x = parse_markdown(plugins.join("\n"))
                params.message = x.message

                // добавляем blockquote-форматирование через TLRPC напрямую
                val blockquote = TLRPC.TL_messageEntityBlockquote()
                blockquote.collapsed = true
                blockquote.offset = 0
                blockquote.length = int(len(x.message.encode(encoding="utf_16_le")) / 2)

                val tlrcpEnts = x.entities.map((ent) -> ent.to_tlrpc_object())
                params.entities = ArrayList(Arrays.asList([blockquote] + tlrcpEnts))
                modify params   // отправляем изменённое сообщение
            } try e {
                log("chelp error: ${e}")
                cancel
            }
        }

        default   // всё остальное — пропускаем без изменений
    }
}

settings {
    input "plf_cmd" {
        text: "Send plugin file command"
        default: ".plf"
    }
    input "chelp_cmd" {
        text: "Send command help command"
        default: ".chelp"
    }
    input "emoji_enabled" {
        text: "Enabled emoji ID"
        default: "5776375003280838798"
    }
    input "emoji_disabled" {
        text: "Disabled emoji ID"
        default: "5778527486270770928"
    }
}
```

### Что здесь интересно

**Функция вне плагина.** `getPythonEngine()` объявлена на верхнем уровне, вне блока `plugin`. Это обычная Python-функция — можно вызывать откуда угодно. Полезно для вспомогательной логики которая не привязана к жизненному циклу плагина.

**Двойное упоминание `hook_send_message`.** Первое — прямо внутри `plugin { }` перед `on_load` — это декларация (говорит компилятору что плагин использует этот хук). Второе — внутри `on_load` — это регистрация (реальный вызов `self.add_on_send_message_hook()`). В простых плагинах достаточно только второго.

**`cancel` отменяет исходное сообщение целиком.** После `client_utils.send_document(...)` мы делаем `cancel` — потому что вместо текстового сообщения уже ушёл файл. Если бы написали `default` — отправился бы и файл, и оригинальный текст `.plf plugin_id`.

**Итерация по Java Map.** `pls.keySet().toArray()` и `pls.values().toArray()` — это Java-методы. Reunion транслирует цепочки вызовов через точку один в один. Подробнее о работе с Java — в разделе [Хуки на Java-методы](https://github.com/shareui/reunion-compiler/tree/main/docs/08_java_hooks.md).


