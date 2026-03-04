# Reunion

Язык и компилятор для написания плагинов к exteraGram и AyuGram.

Вместо того чтобы писать Python-boilerplate вручную — пишешь на Reunion, компилятор генерирует `.plugin` файл.

```
metainfo {
    id: "ghost_mode"
    name: "Ghost Mode"
    version: "1.0.0"
    author: "you"
    description: "Hides typing status"
    min_version: "11.12.0"
}

import base_plugin(BasePlugin, HookResult, HookStrategy)

plugin GhostMode {
    fun on_load() {
        hook "TL_messages_setTyping"
    }

    fun pre_request(request_name, account, request) {
        cancel
    }
}
```

```bash
pip install reunionc
reuc ghost_mode.reu   # → ghost_mode.plugin
```

## Ссылки

- [Документация](https://github.com/shareui/reunion-compiler/tree/main/docs)  
- [Задать вопрос](https://t.me/reunionreu/3)  
- [Предложить/Сообщить о баге](https://t.me/reunionreu/6)

## Установка

```bash
pip install reunionc
```

Или из исходников:

```bash
git clone https://github.com/shareui/reunion-compiler
cd reunion-compiler/pip-package
pip install -e .
```

## Использование

```bash
reuc my_plugin.reu          # компилировать
reuc my_plugin.reu --check  # только проверить синтаксис
```
