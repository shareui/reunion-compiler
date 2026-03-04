# Hook Utilities — работа с приватными полями

`hook_utils` содержит не только `find_class` но и функции для доступа к приватным полям Java-объектов через рефлексию. Это расширение возможностей Xposed-хуков — можно читать и менять внутреннее состояние объектов без перехвата методов.

Подробнее на официальной странице документации exteraGram: [https://plugins.exteragram.app/docs/hook-utils](https://plugins.exteragram.app/docs/hook-utils).

> **Используй с осторожностью.** Рефлексия — мощный но хрупкий инструмент. Она может сломаться при обновлении приложения если изменятся имена полей или структура классов. Всегда оборачивай вызовы в `sus/try` и проверяй возвращаемые значения на `null`.

```
import hook_utils(find_class, get_private_field, set_private_field, get_static_private_field, set_static_private_field)
```

---

## `find_class` — найти класс

Уже описан в разделе [Хуки на Java-методы](https://github.com/shareui/reunion-compiler/tree/main/docs/08_java_hooks.md). Возвращает Java Class объект по полному имени, или `null` если класс не найден.

```
import hook_utils(find_class)

val cls = find_class("org.telegram.ui.ActionBar.ActionBar")
if not cls {
    log("Class not found")
    return
}
log("Found: ${cls.getName()}")
```

---

## `get_private_field` — читать приватное поле объекта

Получает значение поля экземпляра — даже приватного (`private`). Ищет по всей иерархии классов.

```
get_private_field(obj, field_name)
```

| Аргумент | Описание |
|---|---|
| `obj` | Java-объект экземпляр |
| `field_name` | Имя поля |

Возвращает значение поля или `null` если поле не найдено.

```
import hook_utils(find_class, get_private_field)
import base_plugin(BasePlugin, HookResult, HookStrategy, MethodHook)

plugin FieldReaderPlugin {
    method_hook ChatActivityHook {
        fun after(param) {
            val chatActivity = param.thisObject
            sus {
                val listView = get_private_field(chatActivity, "chatListView")
                if listView {
                    log("chatListView found: ${listView}")
                }
            } try e {
                log("Field access failed: ${e.message}")
            }
        }
    }

    fun on_load() {
        sus {
            val cls = find_class("org.telegram.ui.ChatActivity")
            if not cls { return }
            hook_all_methods(cls, "onResume", ChatActivityHook)
        } try e {
            log("Hook failed: ${e.message}")
        }
    }
}
```

---

## `set_private_field` — изменить приватное поле объекта

Устанавливает новое значение поля экземпляра.

```
set_private_field(obj, field_name, new_value)
```

| Аргумент | Описание |
|---|---|
| `obj` | Java-объект экземпляр |
| `field_name` | Имя поля |
| `new_value` | Новое значение |

Возвращает `true` если успешно, `false` если поле не найдено.

```
import hook_utils(find_class, set_private_field)

sus {
    val userObj = getUserObject()   // какой-то Java-объект пользователя
    val ok = set_private_field(userObj, "premium", true)
    if ok {
        log("Field set successfully")
    }
} try e {
    log("Failed: ${e.message}")
}
```

---

## `get_static_private_field` — читать статическое поле класса

Аналог `get_private_field`, но для статических полей (`static`). Принимает класс, а не экземпляр.

```
get_static_private_field(clazz, field_name)
```

| Аргумент | Описание |
|---|---|
| `clazz` | Java Class объект (результат `find_class`) |
| `field_name` | Имя статического поля |

Возвращает значение поля или `null`.

```
import hook_utils(find_class, get_static_private_field)

sus {
    val ExteraConfig = find_class("com.exteragram.messenger.ExteraConfig")
    if not ExteraConfig { return }

    val configLoaded = get_static_private_field(ExteraConfig, "configLoaded")
    log("Config loaded: $configLoaded")
} try e {
    log("Failed: ${e.message}")
}
```

---

## `set_static_private_field` — изменить статическое поле класса

Устанавливает новое значение статического поля.

```
set_static_private_field(clazz, field_name, new_value)
```

| Аргумент | Описание |
|---|---|
| `clazz` | Java Class объект |
| `field_name` | Имя статического поля |
| `new_value` | Новое значение |

Возвращает `true` если успешно, `false` если нет.

```
import hook_utils(find_class, set_static_private_field)

sus {
    val BuildVars = find_class("org.telegram.messenger.BuildVars")
    if not BuildVars { return }

    val ok = set_static_private_field(BuildVars, "DEBUG_VERSION", true)
    if ok {
        log("DEBUG_VERSION enabled")
    }
} try e {
    log("Failed: ${e.message}")
}
```

---

## Разница между методами

| Функция | Тип поля | Тип объекта |
|---|---|---|
| `get_private_field` | Поле экземпляра | Объект (`param.thisObject`, `param.args[n]`) |
| `set_private_field` | Поле экземпляра | Объект |
| `get_static_private_field` | Статическое поле | Класс (результат `find_class`) |
| `set_static_private_field` | Статическое поле | Класс |

**Поле экземпляра** — существует отдельно для каждого объекта, как обычный атрибут в Python.

**Статическое поле** — одно на весь класс, не привязано к конкретному экземпляру. В Java обычно объявляются как `static`.
