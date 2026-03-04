# Синтаксис Reunion

Reunion — не новый язык с нуля. Это тонкий слой поверх Python: убирает boilerplate, добавляет удобный синтаксис для специфики плагинов, и компилируется в обычный Python-файл. Всё что ты знаешь про Python — работает.

Этот раздел устроен как справочник: каждая конструкция показана с эквивалентом на Python.

---

## Общее

Одна инструкция — одна строка. Несколько на одной строке — через `;`.

```
val x = 1
val y = 2; val z = 3
```

Блоки — **фигурные скобки**. Это отличие от Python где используются отступы — в Reunion блоки всегда в `{ }`.

```
if condition {
    doSomething()
}
```

Комментарии:
```
// однострочный

/*
    многострочный
*/
```

---

## Переменные

`val` — нельзя переприсвоить (как `final` / `const`). `var` — можно менять.

```
val name = "Ghost Mode"     // неизменяемая
var counter = 0             // изменяемая
var active = true
var result = null
```

Компилятор **проверяет** — если попытаешься переписать `val`, получишь ошибку компиляции.

> В Python нет разделения на изменяемые и неизменяемые переменные. В Reunion это сделано намеренно, чтобы избежать случайных перезаписей.

---

## Строки

Оба варианта кавычек работают:

```
val city = "Moscow"
val city = 'Moscow'
```

### Интерполяция

Вставка переменных прямо в строку через `$` или `${}`:

```
val greeting = "Hello, $name"
val info = "Length: ${name.length}, upper: ${name.upper()}"
```

Компилятор превращает это в Python f-string: `f"Hello, {name}"`.

### Многострочные строки

```
val message = """
    Weather in $city:
    Temp: ${temp}°C
"""
```

### Конкатенация и методы строк

```
val full = "Hello, " + name + "!"

val upper = city.upper()
val trimmed = city.strip()
val parts = message.split(" ", 1)
val starts = message.startswith(".wt")
val length = message.length
val joined = ["a", "b", "c"].join(", ")
```

Это обычные Python-методы строк — компилятор передаёт их один в один.

---

## Числа и булевы

```
val port = 5678
val ratio = 0.75
val big = 1_000_000

val enabled = true
val disabled = false
```

Арифметика: `+`, `-`, `*`, `/`, `%`, `**` (степень), `//` (целочисленное деление).

Логика: `and`, `or`, `not`. Сравнения: `==`, `!=`, `<`, `>`, `<=`, `>=`.

---

## Коллекции

### Список

```
val cities = ["Moscow", "London", "Tokyo"]
val empty = []

val first = cities[0]
val last = cities[-1]
val slice = cities[1:3]

cities.append("Berlin")
cities.remove("London")
val count = cities.length
val has = "Moscow" in cities

for city in cities {
    log(city)
}

for i, city in cities.enumerate() {
    log("$i: $city")
}

val lengths = cities.map((c) -> c.length)
val long = cities.filter((c) -> c.length > 5)
```

### Словарь

```
val config = {
    "timeout": 30,
    "city": "Moscow"
}

val timeout = config["timeout"]
val city = config.get("city", "Moscow")

config["timeout"] = 60
config.delete("city")

for key, value in config.items() {
    log("$key = $value")
}
```

### Множество

```
val hooks = {"TL_messages_setTyping", "TL_account_updateStatus"}
val empty_set = set()

hooks.add("TL_messages_sendMessage")
hooks.remove("TL_account_updateStatus")
val has = "TL_messages_setTyping" in hooks
```

---

## Функции

```
fun greet(name) {
    return "Hello, $name"
}

fun fetchWeather(city = "Moscow") {
    // параметр по умолчанию
}

fun double(x) = x * 2   // однострочная форма
```

Именованные аргументы при вызове:

```
fetchWeather(city = "London")
```

Лямбды:

```
val shout = (text) -> text.upper()
val add = (a, b) -> a + b

val lengths = cities.map((c) -> c.length)
val long = cities.filter((c) -> c.length > 5)
```

---

## Управляющие конструкции

### if / else if / else

```
if condition {
    doSomething()
} else if otherCondition {
    doOther()
} else {
    fallback()
}
```

Как выражение (аналог тернарного оператора):

```
val label = if isOnline then "Online" else "Offline"
```

### switch

Аналог `match/case` в Python 3.10+, но работает на всех версиях:

```
switch requestName {
    "TL_messages_setTyping"                              -> blockRequest()
    "TL_messages_setTyping", "TL_account_updateStatus"  -> handleBoth()
    else                                                 -> passThrough()
}
```

Несколько значений через запятую в одной ветке — это OR.

Как выражение:

```
val label = switch status {
    "online"  -> "Online"
    "offline" -> "Offline"
    else      -> "Unknown"
}
```

### Циклы

```
for item in collection {
    process(item)
}

while condition {
    doSomething()
}
```

`break`, `continue` — как в Python.

---

## Обработка ошибок

Reunion переименовывает `try/except` чтобы не конфликтовать с ключевым словом `try` для перехвата хуков:

| Reunion | Python | Смысл |
|---|---|---|
| `sus` | `try` | Блок, который может упасть |
| `try` | `except` | Перехват ошибки |
| `raise` | `raise` | Выбросить ошибку |
| `finally` | `finally` | Выполняется всегда |

```
sus {
    val data = fetchWeather(city)
    if data == null {
        raise ValueError("Empty response")
    }
    return formatWeather(data, city)
} try ValueError as e {
    log("Value error: ${e.message}")
    return null
} try e {
    log("Unexpected: ${e.message}")
    return null
} finally {
    log("done")
}
```

Без имени переменной:

```
sus {
    riskyOp()
} try {
    log("something went wrong")
}
```

---

## Импорты

```
import requests
import base_plugin(BasePlugin, HookResult, HookStrategy)
import ui.settings(Switch, Input, Selector)
import hook_utils(find_class)
```

Импорт конкретных имён — через скобки. Компилятор разворачивает в `from module import Name1, Name2`.

### Импорты Java и Android

Java-классы импортируются так же — просто указываешь полный путь:

```
import java.lang(Long, Boolean)
import java.lang(String as JString)    // алиас — чтобы не конфликтовало с Python str
import java.io(File)
import java.util(ArrayList, Arrays)
import org.telegram.tgnet(TLRPC)
import org.telegram.messenger(ApplicationLoader, FileLoader)
import com.exteragram.messenger.plugins(PluginsController)
import android.widget(Toast)
import android.content(Context)
```

Компилятор генерирует `from java.lang import Long, Boolean` и так далее. Что это за классы и как они работают — это дело среды выполнения внутри приложения. Компилятор просто транслирует.

---

## Блок `raw`

Если нужно написать что-то что Reunion пока не умеет — блок `raw`. Содержимое вставляется в выходной файл **дословно**, без какого-либо анализа:

```
raw {
    import hashlib

    def compute_hash(text):
        return hashlib.md5(text.encode()).hexdigest()
}
```

`raw` может стоять в любом месте файла. Внутри — полноценный Python. Используй когда нужен сложный низкоуровневый код или конструкция которой нет в Reunion.

---

## Ошибки компилятора

Все ошибки выводятся с точным указанием строки и столбца в `.reu` файле:

```
ReunionSyntaxError at ghost_mode.reu:12:5
  Unexpected token "=>" — did you mean "->"?

ReunionSemanticError at ghost_mode.reu:18:9
  Setting "force_ofline" is not declared in settings block.

ReunionWarning at ghost_mode.reu:7:5
  Hook "TL_account_updateStatus" is registered but has no handler.
```

- **SyntaxError** — неверная структура текста, компиляция останавливается немедленно
- **SemanticError** — синтаксис верный, но логика некорректная. Компилятор собирает **все** такие ошибки за один проход и показывает разом
- **Warning** — код корректен, но выглядит подозрительно. Компиляция продолжается

---

## Полное соответствие Python → Reunion

| Python | Reunion |
|---|---|
| `x = 1` (изменяемая) | `var x = 1` |
| `x = 1` (неизменяемая) | `val x = 1` |
| `f"Hello {name}"` | `"Hello $name"` |
| `try:` | `sus {` |
| `except Exception as e:` | `try e {` |
| `from mod import A, B` | `import mod(A, B)` |
| `from java.lang import String as JString` | `import java.lang(String as JString)` |
| `# comment` | `// comment` |
| `True / False` | `true / false` |
| `None` | `null` |
