# Хуки на сетевые запросы

Telegram общается с серверами через запросы определённых типов. У каждого действия — свой тип: набор текста, отправка сообщения, смена статуса онлайн, загрузка файла. Хуки на сетевые запросы позволяют перехватить любой из них — до отправки или после получения ответа.

---

## Что такое TL-запросы

TL расшифровывается как Type Language — это внутренний протокол Telegram. Каждое действие приложения — это объект определённого типа с полями. Например:

- `TL_messages_setTyping` — «пользователь набирает текст»
- `TL_account_updateStatus` — «обновить статус онлайн/офлайн»
- `TL_messages_sendMessage` — «отправить сообщение»
- `TL_messages_readHistory` — «прочитать историю»

Тебе не нужно знать протокол досконально. Достаточно знать **имя** нужного запроса — его ты и указываешь при регистрации хука.

---

## Регистрация хуков

В `on_load` перечисляешь какие запросы хочешь перехватывать:

```
plugin GhostMode {
    fun on_load() {
        hook "TL_messages_setTyping"
        hook "TL_messages_setEncryptedTyping"
        hook "TL_account_updateStatus"
    }
}
```

После этого при каждом таком запросе будут вызываться твои обработчики `pre_request` и/или `post_request`.

---

## `pre_request` — перехват до отправки

Вызывается **перед** тем как запрос уйдёт на сервер. Здесь можно отменить запрос, изменить его поля, или пропустить как есть.

Сигнатура:

```
fun pre_request(request_name, account, request) {
    // request_name — строка с именем типа, например "TL_messages_setTyping"
    // account      — номер аккаунта (если используется multi-account)
    // request      — объект запроса, можно читать и менять его поля
}
```

Пример — Ghost Mode, блокирует отправку статуса «печатает» и подменяет статус офлайн:

```
plugin GhostMode {
    fun on_load() {
        hook "TL_messages_setTyping"
        hook "TL_messages_setEncryptedTyping"
        hook "TL_account_updateStatus"
    }

    fun pre_request(request_name, account, request) {
        if request_name in ["TL_messages_setTyping", "TL_messages_setEncryptedTyping"] {
            if setting("dont_send_typing", true) {
                log("Blocking: $request_name")
                cancel
            }
        }

        if request_name == "TL_account_updateStatus" {
            if setting("force_offline", true) {
                request.offline = true
                modify request
            }
        }

        default
    }
}
```

### Что делает `modify request`

`request` — это Java-объект. У него есть поля, соответствующие полям TL-типа. В примере выше `request.offline = true` меняет поле объекта `TL_account_updateStatus` — и запрос уйдёт уже с изменёнными данными.

Просто присвоить поле недостаточно — нужно явно сказать `modify request`, иначе компилятор не сгенерирует нужный `HookResult`.

---

## `post_request` — перехват после ответа

Вызывается **после** того как сервер вернул ответ. Здесь уже нельзя отменить запрос — он уже выполнился. Можно читать ответ, логировать, реагировать на ошибки.

Сигнатура:

```
fun post_request(request_name, account, response, error) {
    // response — объект ответа от сервера (null если была ошибка)
    // error    — объект ошибки (null если всё прошло успешно)
}
```

Пример — логируем успешную отправку сообщения:

```
fun post_request(request_name, account, response, error) {
    if request_name == "TL_messages_sendMessage" {
        if error == null {
            log("Message sent successfully")
        } else {
            log("Send failed: ${error}")
        }
    }
    default
}
```

---

## Таблица терминаторов

| Терминатор | В `pre_request` | В `post_request` |
|---|---|---|
| `default` | Запрос уходит как есть | Обработка продолжается как обычно |
| `modify request` | Запрос уходит с изменёнными полями | — |
| `cancel` | Запрос **не отправляется** | — |

В `post_request` только `default` имеет смысл — запрос уже выполнился.

Если ни одного терминатора нет в конце — компилятор автоматически добавит `default`. Но если есть ветки без терминатора — будет ошибка.

---

## Полный пример: Ghost Mode

```
metainfo {
    id: "ghost_mode"
    name: "Ghost Mode"
    version: "1.0.0"
    author: "you"
    description: "Hides typing status and forces offline mode"
    min_version: "11.12.0"
}

import base_plugin(BasePlugin, HookResult, HookStrategy)
import ui.settings(Switch)

plugin GhostMode {
    fun on_load() {
        hook "TL_messages_setTyping"
        hook "TL_messages_setEncryptedTyping"
        hook "TL_account_updateStatus"
        hook "TL_messages_sendMessage"
    }

    fun pre_request(request_name, account, request) {
        if request_name in ["TL_messages_setTyping", "TL_messages_setEncryptedTyping"] {
            if setting("dont_send_typing", true) {
                cancel
            }
        }

        if request_name == "TL_account_updateStatus" {
            if setting("force_offline", true) {
                request.offline = true
                modify request
            }
        }

        default
    }

    fun post_request(request_name, account, response, error) {
        if request_name == "TL_messages_sendMessage" {
            if error == null {
                log("Message sent!")
            }
        }
        default
    }
}

settings {
    switch "dont_send_typing" {
        text: "Don't send typing status"
        default: true
        subtext: "Prevents sending typing indicators to other users"
        icon: "msg_typing"
    }

    switch "force_offline" {
        text: "Always appear offline"
        default: true
    }
}
```

---

## Где найти имена TL-запросов

Имена всех TL-типов есть в исходном коде Telegram. Самый простой способ найти нужное — поискать в репозитории [TelegramAndroid](https://github.com/DrKLO/Telegram) по ключевым словам связанным с нужным действием.

Часто используемые:

| Действие | Запрос |
|---|---|
| Набор текста | `TL_messages_setTyping` |
| Набор текста в зашифрованном чате | `TL_messages_setEncryptedTyping` |
| Статус онлайн/офлайн | `TL_account_updateStatus` |
| Отправка сообщения | `TL_messages_sendMessage` |
| Прочитать сообщения | `TL_messages_readHistory` |
| Прочитать в зашифрованном чате | `TL_messages_readEncryptedHistory` |
| Удалить сообщения | `TL_messages_deleteMessages` |
| Реакция на сообщение | `TL_messages_sendReaction` |
