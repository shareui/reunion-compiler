# Ошибки компилятора и CLI

Компилятор Reunion выдаёт три вида диагностики — ошибки синтаксиса, семантические ошибки и предупреждения. Каждая указывает точную позицию в файле.

---

## Формат сообщений

```
ReunionSyntaxError at ghost_mode.reu:12:5
  Unexpected token "=>" — did you mean "->"?
  |
  | 12 |     val fn = (x) => x * 2
  |         ^

ReunionSemanticError at ghost_mode.reu:31:9
  Setting key "force_ofline" is not declared in settings block.
  |
  | 31 |         if setting("force_ofline", true) {
  |             ^

ReunionWarning at ghost_mode.reu:7:5
  Hook "TL_account_updateStatus" is registered but has no handler (pre_request or post_request).
```

Формат: `тип` → `файл:строка:столбец` → описание → фрагмент кода с подчёркиванием.

---

## Типы диагностики

### `ReunionSyntaxError`

Неверная структура текста — компилятор не может разобрать файл. Компиляция немедленно останавливается на первой синтаксической ошибке.

Частые причины:
- незакрытая скобка или блок `{ }`
- неверный оператор (`=>` вместо `->`)
- неожиданный токен в выражении

### `ReunionSemanticError`

Синтаксис верный, но логика некорректная. Компилятор **собирает все** такие ошибки за один проход и показывает разом — не нужно компилировать несколько раз чтобы увидеть все проблемы.

Частые причины:
- обращение к ключу настройки которого нет в `settings` блоке
- переприсвоение `val`
- отсутствие терминатора на каком-то пути выполнения в хуке
- использование `on_send_message` без `hook_send_message` в `on_load`

### `ReunionWarning`

Код корректен, компиляция продолжается. Предупреждение означает что что-то выглядит подозрительно.

Частые причины:
- хук зарегистрирован, но нет обработчика `pre_request` / `post_request`
- настройка объявлена в `settings`, но нигде не читается через `setting()`
- неизвестное поле в блоке `metainfo`

---

## CLI

### Основные команды

```bash
# скомпилировать файл → рядом появится .plugin
reuc my_plugin.reu

# только проверить, не создавать файл
reuc my_plugin.reu --check

# подробный вывод: токены и AST (для отладки)
reuc my_plugin.reu --verbose

# справка
reuc --help
```

Запуск без установки пакета:

```bash
python -m compiler.src.main my_plugin.reu
python -m compiler.src.main my_plugin.reu --check
```

### Коды выхода

| Код | Значение |
|---|---|
| `0` | Успех |
| `1` | Ошибка компиляции (SyntaxError или SemanticError) |

Ненулевой код при ошибках позволяет интегрировать компилятор в CI/CD — скрипт сборки автоматически упадёт если плагин не компилируется.

---

## Частые ошибки и решения

**`Setting key "key" is not declared in settings block`**

Обращаешься через `setting("key")` к ключу которого нет в блоке `settings`. Проверь написание — опечатка в имени ключа.

```
// ошибка — опечатка
val cmd = setting("plf_cnd", ".plf")

// правильно
val cmd = setting("plf_cmd", ".plf")
```

---

**`Cannot reassign val`**

Пытаешься изменить переменную объявленную как `val`. Замени на `var`.

```
val counter = 0
counter = counter + 1   // ошибка

var counter = 0
counter = counter + 1   // OK
```

---

**`Missing terminator on some execution path`**

Не все ветки `if` заканчиваются терминатором (`cancel`, `modify`, `default`) внутри обработчика хука.

```
// ошибка — ветка else if не имеет терминатора
fun pre_request(request_name, account, request) {
    if request_name == "TL_messages_setTyping" {
        cancel
    } else if request_name == "TL_account_updateStatus" {
        request.offline = true
        modify request
    }
    // забыли default для всех остальных запросов
}

// правильно
fun pre_request(request_name, account, request) {
    if request_name == "TL_messages_setTyping" {
        cancel
    } else if request_name == "TL_account_updateStatus" {
        request.offline = true
        modify request
    }
    default
}
```

---

**`on_send_message defined but hook_send_message not called in on_load`**

Написал обработчик `on_send_message`, но не зарегистрировал хук:

```
// ошибка
fun on_load() {
    log("loaded")
}

fun on_send_message(account, params) { ... }

// правильно
fun on_load() {
    hook_send_message
}

fun on_send_message(account, params) { ... }
```

---

**`Expected 'RPAREN' but got 'as'`**

Старая версия компилятора не поддерживает алиасы в импортах. Обнови компилятор.

```
// требует актуальной версии
import java.lang(String as JString)
```

---

**`Unexpected token '//'`**

Комментарий внутри выражения. В Reunion `//` — однострочный комментарий, он должен стоять на отдельной строке или после инструкции, но не посередине выражения.
