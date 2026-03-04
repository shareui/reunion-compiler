# Классы Telegram

Справочник часто используемых внутренних классов Telegram. Это Java-классы внутри приложения — к ним можно обращаться напрямую из плагина или хукать их методы.

Рекомендуется иметь локальную копию исходников Telegram открытую в Android Studio — так удобнее смотреть сигнатуры методов и поля классов. Репозиторий: [DrKLO/Telegram](https://github.com/DrKLO/Telegram).

---

## Основные классы UI

### `LaunchActivity`

```
import: org.telegram.ui.LaunchActivity
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/ui/LaunchActivity.java)

Точка входа приложения — здесь происходит инициализация. Также здесь обрабатываются кастомные deep links (`tg://...`). Если нужно перехватить открытие ссылки — хукай методы этого класса.

---

### `ProfileActivity`

```
import: org.telegram.ui.ProfileActivity
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/ui/ProfileActivity.java)

Фрагмент профиля пользователя или канала. Если плагин добавляет кнопки или элементы на страницу профиля — работа идёт с этим классом.

---

### `ChatActivity`

```
import: org.telegram.ui.ChatActivity
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java)

Фрагмент чата — отрисовка и вся функциональность. Хукать методы этого класса нужно если хочешь влиять на отображение чата, панель ввода, заголовок.

---

### `ChatMessageCell`

```
import: org.telegram.ui.Cells.ChatMessageCell
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/ui/Cells/ChatMessageCell.java)

Отвечает за отрисовку одного сообщения в чате. Если нужно менять внешний вид сообщений — хукай методы этого класса.

---

## Контроллеры и хелперы

### `MessagesController`

```
import: org.telegram.messenger.MessagesController
// или через client_utils:
import client_utils(get_messages_controller)
val mc = get_messages_controller()
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/messenger/MessagesController.java)

Центральный контроллер приложения. Содержит методы для управления состоянием — загрузка диалогов, контактов, работа с чатами. Самый большой класс в кодовой базе.

---

### `MessagesStorage`

```
import: org.telegram.messenger.MessagesStorage
// или через client_utils:
import client_utils(get_messages_storage)
val ms = get_messages_storage()
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/messenger/MessagesStorage.java)

Управляет локальной SQLite базой данных. Через поле `database` можно выполнять произвольные SQL-запросы — читать и писать локальный кэш сообщений.

```
val storage = get_messages_storage()
val db = storage.database
// db.executeQuery(...) — прямой доступ к SQLite
```

---

### `SendMessagesHelper`

```
import: org.telegram.messenger.SendMessagesHelper
// или через client_utils:
import client_utils(get_send_messages_helper)
val smh = get_send_messages_helper()
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java)

Содержит методы для отправки всех видов сообщений — текст, файлы, фото, голосовые. Низкоуровневая альтернатива функциям из `client_utils` когда нужен точный контроль над параметрами отправки.

---

### `AndroidUtilities`

```
import org.telegram.messenger(AndroidUtilities)
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/messenger/AndroidUtilities.java)

Набор статических утилит: конвертация dp↔px, работа с размерами экрана, форматирование размеров файлов, работа с буфером обмена, запуск на UI-потоке и многое другое.

```
import org.telegram.messenger(AndroidUtilities)

val px = AndroidUtilities.dp(16)          // 16dp → пиксели
val formatted = AndroidUtilities.formatFileSize(1024 * 1024)  // "1 MB"
```

---

## Модели данных

### `MessageObject`

```
import org.telegram.messenger(MessageObject)
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/messenger/MessageObject.java)

Обёртка над `TLRPC.Message`. Добавляет вспомогательные методы и кэшированные поля поверх сырого TL-объекта. Именно этот класс приходит в `context["message"]` в обработчиках контекстного меню.

```
menu_item {
    type: MESSAGE_CONTEXT_MENU
    text: "Log message"
    on_click: (context) -> {
        val msg = context.get("message")   // это MessageObject
        if msg {
            log("ID: ${msg.getId()}")
            log("Text: ${msg.messageText}")
            log("From: ${msg.getSenderId()}")
            log("Is out: ${msg.isOut()}")
        }
    }
}
```

---

### `TLRPC`

```
import org.telegram.tgnet(TLRPC)
```

Путь в исходниках: `TMessagesProj/src/main/java/org/telegram/tgnet/`

Содержит все TL-модели — классы для каждого типа запроса и ответа в протоколе Telegram. Основные файлы: `TLRPC.java` и дополнительные модели рядом.

Человекочитаемый список типов: [corefork.telegram.org/schema](https://corefork.telegram.org/schema) (не всегда актуален — приоритет у исходников).

Часто используемые классы:

| Класс | Что это |
|---|---|
| `TLRPC.TL_messageEntityBold` | Жирный текст |
| `TLRPC.TL_messageEntityItalic` | Курсив |
| `TLRPC.TL_messageEntityCode` | Инлайн-код |
| `TLRPC.TL_messageEntityPre` | Блок кода |
| `TLRPC.TL_messageEntityBlockquote` | Цитата / blockquote |
| `TLRPC.TL_messageEntityTextUrl` | Текстовая ссылка |
| `TLRPC.TL_messageEntityCustomEmoji` | Кастомный эмодзи |
| `TLRPC.Message` | Сырое сообщение |
| `TLRPC.User` | Пользователь |
| `TLRPC.Chat` | Чат или канал |

Пример создания сущности форматирования вручную:

```
import org.telegram.tgnet(TLRPC)
import java.util(ArrayList, Arrays)

val bold = TLRPC.TL_messageEntityBold()
bold.offset = 0
bold.length = 5   // первые 5 символов — жирные

params.message = "Hello world"
params.entities = ArrayList(Arrays.asList([bold]))
modify params
```

---

## UI-компоненты

### `AlertDialog`

```
import: org.telegram.ui.ActionBar.AlertDialog
// в плагинах используй обёртку:
import ui.alert(AlertDialogBuilder)
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/ui/ActionBar/AlertDialog.java)

Базовый класс диалогов. Для плагинов рекомендуется использовать `AlertDialogBuilder` из `ui.alert` — он предоставляет удобный API поверх нативного класса. Прямой доступ к `AlertDialog` нужен только для продвинутых сценариев.

---

### `BulletinFactory`

```
import: org.telegram.ui.Components.BulletinFactory
// в плагинах используй обёртку:
import ui.bulletin(BulletinHelper)
```

[Посмотреть на GitHub](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/ui/Components/BulletinFactory.java)

Фабрика для создания всплывающих уведомлений снизу экрана. Для плагинов рекомендуется `BulletinHelper` из `ui.bulletin`. Прямой доступ к `BulletinFactory` нужен для кастомных типов уведомлений которых нет в `BulletinHelper`.

---

## Как искать нужные методы

Когда знаешь класс но не знаешь конкретный метод:

1. Открой файл класса на GitHub или в Android Studio
2. Ищи по ключевым словам через `Ctrl+F`
3. Смотри сигнатуру — типы параметров нужны для `getDeclaredMethod`

```
// нашёл метод: public static String formatFileSize(long size, boolean removeZero, boolean makeShort)
// импортируем нужные типы и хукаем:

import java.lang(Long, Boolean)
import org.telegram.messenger(AndroidUtilities)

fun on_load() {
    sus {
        val cls = find_class("org.telegram.messenger.AndroidUtilities")
        val method = cls.getClass().getDeclaredMethod(
            "formatFileSize",
            Long.TYPE,
            Boolean.TYPE,
            Boolean.TYPE
        )
        hook_method(method, MySizeHook)
    } try e {
        log("Failed: ${e.message}")
    }
}
```
