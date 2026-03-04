# File Utilities — работа с файлами

`file_utils` предоставляет вспомогательные функции для работы с файлами и директориями: стандартные пути Telegram, чтение/запись файлов, листинг директорий.

Подробнее на официальной странице документации exteraGram: [https://plugins.exteragram.app/docs/file-utils](https://plugins.exteragram.app/docs/file-utils).

---

## Стандартные директории

Telegram хранит файлы в предсказуемых местах. Эти функции возвращают абсолютные пути к стандартным директориям — не нужно составлять пути вручную.

```
import file_utils(
    get_plugins_dir,
    get_cache_dir,
    get_files_dir,
    get_images_dir,
    get_videos_dir,
    get_audios_dir,
    get_documents_dir
)

val pluginsDir   = get_plugins_dir()     // директория плагинов
val cacheDir     = get_cache_dir()       // основной кэш Telegram
val filesDir     = get_files_dir()       // общие файлы
val imagesDir    = get_images_dir()      // изображения
val videosDir    = get_videos_dir()      // видео
val audiosDir    = get_audios_dir()      // аудио
val documentsDir = get_documents_dir()   // документы
```

Типичный паттерн — создать поддиректорию для данных своего плагина внутри директории плагинов:

```
import file_utils(get_plugins_dir, ensure_dir_exists)
import os

val dataDir = os.path.join(get_plugins_dir(), "my_plugin_data")
ensure_dir_exists(dataDir)
```

---

## Работа с директориями

### `ensure_dir_exists` — создать директорию если не существует

```
ensure_dir_exists(path)
```

Создаёт директорию по указанному пути вместе со всеми родительскими директориями если они не существуют. Аналог `os.makedirs(path, exist_ok=True)`, но безопаснее.

```
import file_utils(ensure_dir_exists, get_plugins_dir)
import os

val myDir = os.path.join(get_plugins_dir(), "weather_cache")
ensure_dir_exists(myDir)
// теперь myDir гарантированно существует
```

---

### `list_dir` — список содержимого директории

```
list_dir(path, recursive=false, include_files=true, include_dirs=false, extensions=null)
```

| Параметр | Тип | Описание |
|---|---|---|
| `path` | `str` | Путь к директории |
| `recursive` | `bool` | Обходить поддиректории рекурсивно. По умолчанию `false` |
| `include_files` | `bool` | Включать файлы в результат. По умолчанию `true` |
| `include_dirs` | `bool` | Включать директории в результат. По умолчанию `false` |
| `extensions` | `list[str]?` | Фильтр по расширениям, например `[".jpg", ".png"]`. По умолчанию `null` — все файлы |

Возвращает список абсолютных путей.

```
import file_utils(list_dir, get_images_dir, get_cache_dir)

// все JPG и PNG в директории изображений
val images = list_dir(
    path: get_images_dir(),
    extensions: [".jpg", ".png"]
)
log("Images: ${len(images)}")

// только поддиректории кэша, рекурсивно
val subdirs = list_dir(
    path: get_cache_dir(),
    recursive: true,
    include_files: false,
    include_dirs: true
)
log("Cache subdirs: ${len(subdirs)}")
```

---

## Работа с файлами

### `write_file` — записать текст в файл

```
write_file(path, content)
```

Записывает строку в файл. Если файл уже существует — перезаписывает. Директория должна существовать.

```
import file_utils(write_file, get_plugins_dir, ensure_dir_exists)
import os

val dataDir = os.path.join(get_plugins_dir(), "my_plugin")
ensure_dir_exists(dataDir)

val logPath = os.path.join(dataDir, "events.log")
write_file(logPath, "Plugin started at ${datetime.now()}")
```

---

### `read_file` — прочитать файл

```
read_file(path)
```

Читает содержимое файла как строку. Возвращает `null` если файл не найден или произошла ошибка.

```
import file_utils(read_file, get_plugins_dir)
import os

val configPath = os.path.join(get_plugins_dir(), "my_plugin", "config.txt")
val content = read_file(configPath)

if content {
    log("Config: $content")
} else {
    log("Config not found, using defaults")
}
```

---

### `delete_file` — удалить файл

```
delete_file(path)
```

Удаляет файл. Возвращает `true` если файл был удалён, `false` если файл не найден или ошибка.

```
import file_utils(delete_file)

val tempPath = "/path/to/temp_file.tmp"
val deleted = delete_file(tempPath)
if deleted {
    log("Temp file removed")
}
```

---

## Полный пример — плагин с файловым кэшем

Плагин который кэширует данные между сессиями через файл:

```
import file_utils(get_plugins_dir, ensure_dir_exists, read_file, write_file)
import os
import json

fun getDataDir() {
    val dir = os.path.join(get_plugins_dir(), "my_plugin_data")
    ensure_dir_exists(dir)
    return dir
}

fun loadCache() {
    val path = os.path.join(getDataDir(), "cache.json")
    val content = read_file(path)
    if not content {
        return {}
    }
    sus {
        return json.loads(content)
    } try e {
        log("Cache parse error: ${e.message}")
        return {}
    }
}

fun saveCache(data) {
    val path = os.path.join(getDataDir(), "cache.json")
    sus {
        write_file(path, json.dumps(data))
    } try e {
        log("Cache save error: ${e.message}")
    }
}

plugin CachedPlugin {
    fun on_load() {
        hook_send_message
        val cache = loadCache()
        log("Loaded ${len(cache)} cached entries")
    }

    fun on_send_message(account, params) {
        if not params.message { default }
        // ... логика с использованием кэша
        default
    }
}
```
