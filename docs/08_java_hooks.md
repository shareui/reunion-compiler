# Хуки на Java-методы

exteraGram написан на Java. Это значит что внутри приложения постоянно вызываются тысячи Java-методов — отрисовка интерфейса, логика чатов, форматирование чисел, проверки, анимации. Xposed-хуки позволяют перехватить вызов **любого** из них.

---

## Зачем это нужно

Хуки на TL-запросы и сообщения покрывают большую часть задач. Но иногда нужно большее:

- Изменить поведение UI-компонента
- Подменить возвращаемое значение какого-то метода
- Перехватить действие которое не выражается через сетевой запрос
- Убрать или заменить какой-то элемент интерфейса

Для всего этого — Xposed-хуки.

Подробнее на официальной странице документации exteraGram: [https://plugins.exteragram.app/docs/xposed-hooking](https://plugins.exteragram.app/docs/xposed-hooking).

---

## Как это устроено

Процесс всегда одинаковый:

1. Найти Java-класс через `find_class`
2. Получить нужный метод через `getDeclaredMethod` (или конструктор через `getDeclaredConstructor`)
3. Определить обработчик — `method_hook` (before/after) или `method_replace` (полная замена)
4. Применить хук через `hook_method` или `hook_all_methods`

---

## `find_class` — найти класс

```
import hook_utils(find_class)

val ActionBar = find_class("org.telegram.ui.ActionBar.ActionBar")
```

`find_class` принимает полное имя Java-класса и возвращает его. Если класс не найден — возвращает `null`. Всегда проверяй результат перед использованием.

```
val cls = find_class("org.telegram.messenger.FileLog")
if not cls {
    log("Class not found")
    return
}
```

---

## Получить метод

После того как нашёл класс — получаешь нужный метод через Java Reflection:

```
// getDeclaredMethod("имя_метода", ...типы_параметров)
val method = ActionBar.getClass().getDeclaredMethod("setTitle", CharSequenceClass)
method.setAccessible(true)   // нужно для non-public методов
```

Типы параметров — это тоже Java-классы. Их нужно либо получить через `find_class`, либо импортировать напрямую:

```
import java.lang(Long, Boolean, String as JString)
import java(jint)   // примитивный int

val CharSequenceClass = find_class("java.lang.CharSequence")
val method = cls.getClass().getDeclaredMethod("formatFileSize", Long.TYPE, Boolean.TYPE)
```

`Long.TYPE`, `Boolean.TYPE` — это Java-примитивы `long` и `boolean` (не объекты). Нужны когда метод принимает примитивный тип, а не обёртку.

Для конструктора:

```
val constructor = cls.getClass().getDeclaredConstructor(ContextClass)
constructor.setAccessible(true)
```

---

## `method_hook` — before и after

`method_hook` позволяет запустить код **до** и/или **после** оригинального метода. Оригинальный метод всё равно вызывается — если только ты явно его не пропустишь через `param.setResult()`.

```
method_hook TitleLogger {
    fun before(param) {
        val title = param.args[0]          // аргументы метода
        log("Title being set: $title")
        param.args[0] = "[Hooked] $title"  // можно менять аргументы
    }

    fun after(param) {
        log("Title was set")
        // param.getResult() — возвращаемое значение (после выполнения)
        // param.setResult(value) — заменить возвращаемое значение
    }
}
```

Можно определить только `before`, только `after`, или оба — как нужно.

### Пропустить оригинальный метод из `before`

Если в `before` вызвать `param.setResult(value)` — оригинальный метод **не выполнится**. Управление сразу перейдёт в `after`.

```
method_hook FormatFileSizeHook {
    fun before(param) {
        val size = param.args[0]
        if size < 1024 {
            param.setResult("${size} bytes")   // оригинальный метод пропускается
        }
        // иначе — оригинальный метод выполнится как обычно
    }
}
```

### Изменить возвращаемое значение из `after`

```
method_hook BuildVarsHook {
    fun after(param) {
        param.setResult(false)   // всегда возвращаем false
    }
}
```

---

## `method_replace` — полная замена

`method_replace` полностью заменяет метод. Оригинальный код вообще не выполняется.

```
method_replace NoOpLogger {
    fun replace(param) {
        // ничего не делаем — метод заглушён
        return null
    }
}
```

Используй когда нужно полностью отключить метод или написать свою реализацию.

---

## Применить хук

После того как определил обработчик — применяешь его в `on_load`:

```
fun on_load() {
    sus {
        val ActionBar = find_class("org.telegram.ui.ActionBar.ActionBar")
        val CharSequence = find_class("java.lang.CharSequence")
        val method = ActionBar.getClass().getDeclaredMethod("setTitle", CharSequence)
        method.setAccessible(true)
        hook_method(method, TitleLogger)
        log("Hooked ActionBar.setTitle()")
    } try e {
        log("Hook failed: ${e.message}")
    }
}
```

`hook_method` — хукает конкретный метод.

`hook_all_methods` — хукает все методы с заданным именем в классе (удобно когда метод перегружен):

```
fun on_load() {
    sus {
        val cls = find_class("org.telegram.ui.ActionBar.ActionBar")
        val hooks = hook_all_methods(cls, "setTitle", TitleLogger)
        log("Hooked ${len(hooks)} methods")
    } try e {
        log("Hook failed: ${e.message}")
    }
}
```

`hook_all_methods` возвращает список объектов `Unhook` — их можно использовать чтобы снять хук позже, но обычно это не нужно.

---

## Объект `param`

| Что | Как |
|---|---|
| Читать аргумент | `param.args[0]`, `param.args[1]`, ... |
| Изменить аргумент | `param.args[0] = newValue` |
| Объект на котором вызван метод | `param.thisObject` |
| Получить возвращаемое значение (в `after`) | `param.getResult()` |
| Установить возвращаемое значение | `param.setResult(value)` |

---

## Три примера — от простого к сложному

### 1. Логировать и изменить аргумент (before)

Перехватываем `ActionBar.setTitle()` и добавляем префикс к каждому заголовку:

```
import base_plugin(BasePlugin, HookResult, HookStrategy, MethodHook)
import hook_utils(find_class)

plugin TitlePrefixPlugin {
    method_hook TitleLogger {
        fun before(param) {
            val title = param.args[0]
            param.args[0] = "[Beta] $title"
        }
    }

    fun on_load() {
        sus {
            val ActionBar = find_class("org.telegram.ui.ActionBar.ActionBar")
            val CharSequence = find_class("java.lang.CharSequence")
            val method = ActionBar.getClass().getDeclaredMethod("setTitle", CharSequence)
            method.setAccessible(true)
            hook_method(method, TitleLogger)
        } try e {
            log("Failed: ${e.message}")
        }
    }
}
```

### 2. Изменить возвращаемое значение (after)

Перехватываем `BuildVars.isMainApp()` и всегда возвращаем `false`:

```
import base_plugin(BasePlugin, HookResult, HookStrategy, MethodHook)
import hook_utils(find_class)

plugin BuildVarsPlugin {
    method_hook BuildVarsHook {
        fun after(param) {
            param.setResult(false)
        }
    }

    fun on_load() {
        sus {
            val BuildVars = find_class("org.telegram.messenger.BuildVars")
            val method = BuildVars.getClass().getDeclaredMethod("isMainApp")
            method.setAccessible(true)
            hook_method(method, BuildVarsHook)
        } try e {
            log("Failed: ${e.message}")
        }
    }
}
```

### 3. Заглушить метод полностью (method_replace)

Отключаем `FileLog.d()` — метод логирования который спамит в logcat:

```
import base_plugin(BasePlugin, HookResult, HookStrategy, MethodReplacement)
import hook_utils(find_class)
import java.lang(String as JString)

plugin NoLogPlugin {
    method_replace NoOpLogger {
        fun replace(param) {
            return null
        }
    }

    fun on_load() {
        sus {
            val FileLog = find_class("org.telegram.messenger.FileLog")
            val method = FileLog.getClass().getDeclaredMethod("d", JString)
            method.setAccessible(true)
            hook_method(method, NoOpLogger)
            log("FileLog.d() silenced")
        } try e {
            log("Failed: ${e.message}")
        }
    }
}
```

---

## Java-импорты в Reunion

Все Java-классы импортируются как обычные модули — через полный путь:

```
import java.lang(Long, Boolean, String as JString)
import java(jint)
import java.io(File)
import java.util(ArrayList, Arrays)
import android.widget(Toast)
import android.content(Context)
import org.telegram.tgnet(TLRPC)
import org.telegram.messenger(ApplicationLoader, FileLoader)
import com.exteragram.messenger.plugins(PluginsController)
```

Алиас `as` нужен когда имя Java-класса конфликтует с Python-именем. `String` — зарезервировано неявно, поэтому обычно пишут `String as JString`. `jint` — примитивный `int` для передачи в методы которые принимают `int`, а не `Integer`.

---

## `raw {}` — когда нужен

Если конструкция не вписывается в синтаксис Reunion — используй блок `raw`. Содержимое вставляется в выходной файл дословно:

```
raw {
    from java.lang import String as JString  # type: ignore

    def my_helper():
        return "raw python here"
}
```

Типичные случаи: сложные статические инициализаторы, декораторы, конструкции которых нет в Reunion. В остальных случаях — лучше нативный синтаксис Reunion.
