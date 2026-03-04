[RU](#ru) | [EN](#en)

---

<a name="ru"></a>

# Введение в Reunion

## Что такое Reunion

Reunion — это экспериментальный язык программирования и компилятор для написания плагинов к [exteraGram](https://github.com/exteraSquad/exteraGram) и [AyuGram](https://github.com/AyuGram/AyuGram4A).

Плагин на Reunion пишется в файле `.reu` и компилируется в `.plugin` — Python-файл, который платформа загружает напрямую.

## Для кого

Reunion предназначен для разработчиков, которые **знают Python**, но сталкиваются с барьерами при написании плагинов напрямую:

- exteraGram API требует знания внутренней архитектуры Telegram-клиента
- Xposed-хуки предполагают понимание Java-рефлексии
- Шаблонный код (`on_plugin_load`, `HookResult`, `MenuItemData` и т.д.) повторяется в каждом плагине

Reunion убирает этот шаблон и даёт синтаксис, близкий к Python, в котором хуки, настройки и меню объявляются декларативно.

## Как это работает

```
plugin.reu  →  reuc  →  plugin.plugin  →  exteraGram
```

Компилятор `reuc` транслирует `.reu` в валидный Python-файл, соответствующий контракту exteraGram API. Никакого рантайма, никаких зависимостей — только исходник и скомпилированный файл.

## Установка

**Требования:** Python 3.11+

```bash
pip install reunionc
```

После установки команда `reuc` доступна глобально.

## Команды

```
reuc                             показать версию компилятора
reuc <file.reu>                  компилировать → <file.plugin>
reuc <file.reu> <out.plugin>     компилировать → указанный файл
reuc --check <file.reu>          проверка синтаксиса без записи файла
reuc --verbose <file.reu>        вывод токенов и AST в stderr
reuc --help                      справка
```

---

<a name="en"></a>

# Introduction to Reunion

## What is Reunion

Reunion is an experimental programming language and compiler for writing plugins for [exteraGram](https://github.com/exteraSquad/exteraGram) and [AyuGram](https://github.com/AyuGram/AyuGram4A).

A Reunion plugin is written in a `.reu` file and compiled to a `.plugin` — a Python file loaded directly by the platform.

## Who it's for

Reunion is designed for developers who **know Python** but face friction writing plugins directly:

- The exteraGram API requires knowledge of the Telegram client's internal architecture
- Xposed hooks require understanding Java reflection
- Boilerplate (`on_plugin_load`, `HookResult`, `MenuItemData`, etc.) repeats in every plugin

Reunion eliminates the boilerplate and provides a Python-like syntax where hooks, settings, and menus are declared declaratively.

## How it works

```
plugin.reu  →  reuc  →  plugin.plugin  →  exteraGram
```

The `reuc` compiler translates `.reu` into a valid Python file conforming to the exteraGram API contract. No runtime, no extra dependencies — just source and compiled output.

## Installation

**Requirements:** Python 3.11+

```bash
pip install reunionc
```

After installation, the `reuc` command is available globally.

## Commands

```
reuc                             show compiler version
reuc <file.reu>                  compile → <file.plugin>
reuc <file.reu> <out.plugin>     compile → specified file
reuc --check <file.reu>          syntax check only, no file written
reuc --verbose <file.reu>        dump tokens and AST to stderr
reuc --help                      help
```
