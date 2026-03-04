# Быстрый старт

В этом разделе ты напишешь первый рабочий плагин, скомпилируешь его и загрузишь в приложение. Без лишней теории — просто шаг за шагом.

---

## Что ты сделаешь

Плагин **NoMoreHttps** — перехватывает исходящие сообщения и автоматически удаляет `https://` и `http://` из ссылок перед отправкой. Простой, полезный, наглядный.

Например, ты пишешь:
```
купи на https://wildberries.ru
```
Отправится:
```
купи на wildberries.ru
```

---

## Шаг 1 — создай файл

Создай файл `nohttps.reu` и вставь в него:

```
metainfo {
    id: "my_nohttps"
    name: "No More Https"
    version: "1.0.0"
    author: "ты"
    description: "Убирает https:// и http:// из отправляемых сообщений"
    min_version: "11.12.0"
}

import base_plugin(BasePlugin, HookResult, HookStrategy)

plugin NoMoreHttps {
    fun on_load() {
        hook_send_message
    }

    fun on_send_message(account, params) {
        if not params.message {
            default
        }

        val original = params.message
        val modified = original.replace("https://", "").replace("http://", "")

        if modified != original {
            params.message = modified
            modify params
        }

        default
    }
}
```

---

## Шаг 2 — скомпилируй

```bash
reuc nohttps.reu
```

Рядом появится файл `nohttps.plugin`. Это и есть плагин — обычный Python-файл.

Если хочешь только проверить синтаксис без создания файла:

```bash
reuc nohttps.reu --check
```

---

## Шаг 3 — загрузи в приложение

Отправь `nohttps.plugin` себе в избранное (Saved Messages) прямо в exteraGram. Приложение распознает файл и предложит установить плагин.

---

## Что здесь происходит — разбор по строкам

### Блок `metainfo`

```
metainfo {
    id: "my_nohttps"
    name: "No More Https"
    ...
}
```

Это паспорт плагина. Приложение читает отсюда название, версию и автора. **`id` должен быть уникальным** — именно по нему приложение отличает плагины друг от друга.

### Импорт

```
import base_plugin(BasePlugin, HookResult, HookStrategy)
```

Подключаем базовый класс и типы результатов. Это нужно в каждом плагине — без этого компилятор не сгенерирует правильный Python.

### Блок `plugin`

```
plugin NoMoreHttps {
    ...
}
```

Это и есть плагин. Внутри — методы. Компилятор превратит это в Python-класс `class NoMoreHttps(BasePlugin)`.

### `on_load` и регистрация хука

```
fun on_load() {
    hook_send_message
}
```

`on_load` вызывается когда плагин включается. `hook_send_message` — говорим приложению: «хочу перехватывать все исходящие сообщения». Без этой строки `on_send_message` просто не будет вызываться.

### Обработчик сообщений

```
fun on_send_message(account, params) {
    ...
}
```

Этот метод вызывается **до того как сообщение ушло на сервер**. `params.message` — текст сообщения. Можно читать, менять, отменять отправку.

### Терминаторы — обязательное завершение

Каждый путь выполнения в обработчике должен заканчиваться одним из трёх:

| Что написать | Что произойдёт |
|---|---|
| `default` | Сообщение отправится как есть |
| `modify params` | Сообщение отправится с изменениями из `params` |
| `cancel` | Сообщение **не отправится** вообще |

Если забудешь — компилятор выдаст ошибку.


