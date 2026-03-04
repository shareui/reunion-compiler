# Доступные библиотеки

Среда выполнения плагинов работает на **Python 3.11**. Ряд библиотек предустановлен и доступен без дополнительной настройки — их можно импортировать напрямую.

---

## Предустановленные библиотеки

| Библиотека | Для чего |
|---|---|
| `requests` | HTTP-запросы. Самая используемая в плагинах — для обращения к внешним API |
| `pillow` | Работа с изображениями — открытие, изменение размера, конвертация форматов |
| `beautifulsoup4` | Парсинг HTML и XML. Импортируется как `from bs4 import BeautifulSoup` |
| `lxml` | Быстрая обработка XML и HTML. Используется как парсер для BeautifulSoup |
| `PyYAML` | Чтение и запись YAML. Импортируется как `import yaml` |
| `packaging` | Утилиты для работы с версиями пакетов (`Version`, `parse`) |
| `debugpy` | Удалённый отладчик от Microsoft. Используется Dev Server для отладки плагинов |

### Примеры импорта

```
import requests
// или в Reunion:
// просто используй как есть — requests уже доступен

import PIL.Image as Image         // pillow
from bs4 import BeautifulSoup     // beautifulsoup4
import yaml                       // PyYAML
from packaging.version import Version
```

---

## Дополнительные библиотеки через `requirements`

Начиная с версии exteraGram **12.4.1** плагины могут подключать pure-Python библиотеки из PyPI через поле `requirements` в `metainfo`. Приложение установит их автоматически при первом запуске плагина.

```
metainfo {
    id: "my_plugin"
    name: "My Plugin"
    version: "1.0.0"
    author: "you"
    description: "..."
    requirements: "mpmath, httpx"    // через запятую
}
```

После этого в коде можно использовать как обычно:

```
import mpmath
import httpx
```

### Ограничения

Поддерживаются только **pure-Python** библиотеки — то есть те которые написаны полностью на Python и не содержат скомпилированного нативного кода (C-расширений).

Примеры которые **работают**: `mpmath`, `httpx`, `pydantic`, `arrow`, `rich`, `pyparsing`.

Примеры которые **не работают**: `numpy`, `scipy`, `cryptography`, `lxml` (уже предустановлен) — они содержат нативные расширения.

Если нужная функциональность недоступна ни через предустановленные библиотеки ни через pure-Python пакеты — альтернатива: реализовать самостоятельно или найти аналог через Java API (доступен через `find_class` и импорты `java.*`, `android.*`).

---

## Стандартная библиотека Python

Вся стандартная библиотека Python 3.11 доступна без ограничений:

```
import os
import re
import json
import pathlib
import threading
import subprocess
import hashlib
import base64
import datetime
import urllib.parse
import collections
// и т.д.
```

Единственное практическое ограничение — операции требующие прав которых нет у приложения (например запись в системные директории). Всё остальное работает.
