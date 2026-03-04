# Client Utils — утилиты клиента

`client_utils` — модуль с функциями для взаимодействия с самим приложением: отправка сообщений и медиа, работа с потоками, доступ к внутренним контроллерам Telegram.

```
import client_utils
// или импортировать конкретные функции:
import client_utils(send_message, run_on_queue, get_last_fragment)
```

---

## Отправка сообщений и медиа

Все функции отправки принимают `peer_id` — числовой ID чата или пользователя. Внутри хука на сообщение его можно взять из `params.peer`.

### Текстовое сообщение

```
import client_utils(send_message)

send_message(peer_id, "Привет!")
send_message(params.peer, "Погода: ${result}")
```

### Фото

```
import client_utils(send_photo)

send_photo(peer_id, "/path/to/image.jpg")
send_photo(peer_id, "/path/to/image.jpg", caption="Вот фото")
```

### Видео

```
import client_utils(send_video)

send_video(peer_id, "/path/to/video.mp4")
send_video(peer_id, "/path/to/video.mp4", caption="Вот видео")
```

### Аудио

```
import client_utils(send_audio)

send_audio(peer_id, "/path/to/song.mp3")
send_audio(peer_id, "/path/to/song.mp3", caption="Трек")
```

Метаданные (название, исполнитель, длительность) извлекаются автоматически из файла.

### Документ / файл

```
import client_utils(send_document)

send_document(peer_id, "/path/to/file.zip")
send_document(peer_id, "/path/to/plugin.plugin", caption="Плагин")
```

---

## Потоки

### `run_on_queue` — фоновый поток

Сетевые запросы, тяжёлые вычисления, файловые операции — всё это нельзя делать на UI-потоке. `run_on_queue` запускает функцию в фоне:

```
import client_utils(run_on_queue)

run_on_queue(() ->
    val result = doHeavyWork()
    log("Done: $result")
)
```

С указанием очереди и задержкой:

```
import client_utils(run_on_queue, GLOBAL_QUEUE)

run_on_queue(() -> doWork(), GLOBAL_QUEUE, 2500)   // через 2.5 секунды
```

Доступные очереди: `PLUGINS_QUEUE` (по умолчанию), `GLOBAL_QUEUE`.

### `run_on_ui_thread` — главный поток

После фоновой работы вернуться на UI-поток — для обновления интерфейса, отправки сообщений, показа диалогов:

```
import android_utils(run_on_ui_thread)
import client_utils(run_on_queue, send_message, get_last_fragment)
import ui.bulletin(BulletinHelper)

run_on_queue(() ->
    val result = fetchData()
    run_on_ui_thread(() ->
        BulletinHelper.show_success("Готово: $result", get_last_fragment())
    )
)
```

> `run_on_ui_thread` находится в `android_utils`, а не в `client_utils`.

### `get_queue_by_name` — прямой доступ к очереди

Если нужно работать с очередью напрямую:

```
import client_utils(get_queue_by_name, PLUGINS_QUEUE)

val queue = get_queue_by_name(PLUGINS_QUEUE)
if queue {
    queue.postRunnable(lambda: doWork())
}
```

---

## Фрагменты и контекст

### `get_last_fragment`

Возвращает текущий активный экран приложения. Нужен для UI-методов — BulletinHelper, AlertDialog:

```
import client_utils(get_last_fragment)

val fragment = get_last_fragment()
val activity = fragment.getParentActivity()
```

---

## Внутренние контроллеры Telegram

Telegram устроен как набор синглтон-контроллеров — каждый отвечает за свою область. Доступ к ним через `client_utils`:

```
import client_utils(
    get_account_instance,
    get_messages_controller,
    get_connections_manager,
    get_send_messages_helper,
    get_user_config,
    get_contacts_controller,
    get_notifications_controller,
    get_file_loader,
    get_messages_storage,
    get_media_data_controller,
    get_location_controller,
    get_secret_chat_helper,
    get_download_controller,
    get_notifications_settings,
    get_notification_center,
    get_media_controller
)
```

Все функции возвращают объект контроллера для текущего аккаунта. Примеры использования:

```
// информация о текущем пользователе
val userConfig = get_user_config()
val currentUser = userConfig.getCurrentUser()
if currentUser {
    log("Logged in as: ${currentUser.first_name} (ID: ${currentUser.id})")
}

// загрузка диалогов
val messagesController = get_messages_controller()
messagesController.loadDialogs(0, 50, true)

// менеджер соединений
val connectionsManager = get_connections_manager()
val dc = connectionsManager.getCurrentDatacenterId()
log("Current DC: $dc")
```

Методы контроллеров — это Java-методы внутреннего API Telegram. Их сигнатуры можно найти в исходном коде [TelegramAndroid](https://github.com/DrKLO/Telegram).

---

## Типичный паттерн: команда с фоновой работой

Полная схема обработки команды которая делает что-то тяжёлое и возвращает результат в чат:

```
import client_utils(send_message, run_on_queue, get_last_fragment)
import android_utils(run_on_ui_thread)
import ui.bulletin(BulletinHelper)

fun on_send_message(account, params) {
    if not params.message { default }
    if not params.message.startswith(".cmd") { default }

    val peer = params.peer
    val arg = params.message.split(" ", 1)

    run_on_queue(() ->
        sus {
            val result = doHeavyWork(arg)
            run_on_ui_thread(() ->
                send_message(peer, result)
            )
        } try e {
            run_on_ui_thread(() ->
                val fragment = get_last_fragment()
                BulletinHelper.show_error("Ошибка: ${e.message}", fragment)
            )
        }
    )

    cancel
}
```
