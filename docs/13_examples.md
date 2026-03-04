# Примеры плагинов

Здесь собраны готовые плагины с разбором — от простых до сложных. Каждый демонстрирует конкретный паттерн который можно взять за основу.

---

## NoMoreHttps — минимальный плагин

Убирает `https://` и `http://` из отправляемых сообщений. Показывает базовую структуру хука на сообщение.

**Что демонстрирует:** `hook_send_message`, изменение `params.message`, терминаторы.

```
metainfo {
    id: "my_nohttps"
    name: "No More Https"
    version: "1.0.0"
    author: "you"
    description: "Removes https:// and http:// from outgoing messages"
    min_version: "11.12.0"
}

import base_plugin(BasePlugin, HookResult, HookStrategy)

plugin NoMoreHttps {
    fun on_load() {
        hook_send_message
    }

    fun on_send_message(account, params) {
        if not params.message {
            default
        }

        val original = params.message
        val modified = original.replace("https://", "").replace("http://", "")

        if modified != original {
            params.message = modified
            modify params
        }

        default
    }
}
```

---

## Ghost Mode — хуки на TL-запросы

Блокирует отправку статуса «печатает» и принудительно выставляет офлайн.

**Что демонстрирует:** `hook`, `pre_request`, `post_request`, `modify request`, `cancel`, настройки типа `switch`.

```
metainfo {
    id: "ghost_mode"
    name: "Ghost Mode"
    version: "1.0.0"
    author: "you"
    description: "Hides typing status and forces offline"
    min_version: "11.12.0"
}

import base_plugin(BasePlugin, HookResult, HookStrategy)
import ui.settings(Switch)

plugin GhostMode {
    fun on_load() {
        hook "TL_messages_setTyping"
        hook "TL_messages_setEncryptedTyping"
        hook "TL_account_updateStatus"
        hook "TL_messages_sendMessage"
    }

    fun pre_request(request_name, account, request) {
        if request_name in ["TL_messages_setTyping", "TL_messages_setEncryptedTyping"] {
            if setting("dont_send_typing", true) {
                cancel
            }
        }

        if request_name == "TL_account_updateStatus" {
            if setting("force_offline", true) {
                request.offline = true
                modify request
            }
        }

        default
    }

    fun post_request(request_name, account, response, error) {
        if request_name == "TL_messages_sendMessage" {
            if error == null {
                log("Message sent!")
            }
        }
        default
    }
}

settings {
    switch "dont_send_typing" {
        text: "Don't send typing status"
        default: true
    }

    switch "force_offline" {
        text: "Always appear offline"
        default: true
    }
}
```

---

## Weather — фоновый запрос и форматирование

Перехватывает команду `.wt [город]`, делает запрос к API в фоне и отправляет результат.

**Что демонстрирует:** `run_on_queue`, `run_on_ui_thread`, `send_message`, `cancel`, чистое разделение логики на функции, `requirements`.

```
metainfo {
    id: "weather"
    name: "Weather"
    version: "1.0.0"
    author: "you"
    description: "Current weather [.wt city]"
    min_version: "11.12.0"
    requirements: "requests"
}

import base_plugin(BasePlugin, HookResult, HookStrategy)
import client_utils(send_message, run_on_queue)
import android_utils(run_on_ui_thread, log)
import requests

fun fetchWeather(city) {
    sus {
        val resp = requests.get(
            "https://wttr.in/${city}?format=j1",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if resp.status_code != 200 { return null }
        return resp.json()
    } try e {
        log("fetch error: ${e.message}")
        return null
    }
}

fun formatWeather(data, city) {
    sus {
        val area = data.get("nearest_area", [{}])[0]
        val name = area.get("areaName", [{}])[0].get("value", city)
        val country = area.get("country", [{}])[0].get("value", "")
        val cur = data.get("current_condition", [{}])[0]
        val temp = cur.get("temp_C", "?")
        val feels = cur.get("FeelsLikeC", "?")
        val desc = cur.get("weatherDesc", [{}])[0].get("value", "?")
        val hum = cur.get("humidity", "?")
        val wind = cur.get("windspeedKmph", "?")
        return "Weather in $name, $country:\n\n• ${temp}°C (feels like ${feels}°C)\n• $desc\n• Humidity: ${hum}%\n• Wind: ${wind} km/h"
    } try e {
        return "Error formatting data"
    }
}

plugin WeatherPlugin {
    fun on_load() {
        hook_send_message
    }

    fun on_send_message(account, params) {
        if not params.message { default }
        if not params.message.startswith(".wt") { default }

        val parts = params.message.strip().split(" ", 1)
        val city = if parts.length > 1 then parts[1].strip() else "Moscow"
        val peer = params.peer

        run_on_queue(() ->
            sus {
                val data = fetchWeather(city)
                val text = if data != null
                    then formatWeather(data, city)
                    else "Failed to fetch weather for '$city'"
                run_on_ui_thread(() -> send_message(peer, text))
            } try e {
                run_on_ui_thread(() -> send_message(peer, "Error: ${e.message}"))
            }
        )

        cancel
    }
}
```

---

## CactusLib Mini — работа с Java API и форматирование

Два режима: `.plf <id>` — отправляет файл плагина в чат, `.chelp` — выводит список всех установленных плагинов с форматированием.

**Что демонстрирует:** Java-импорты (`File`, `ArrayList`, `Arrays`, `TLRPC`), `PluginsController`, `parse_markdown`, TLRPC-сущности вручную, работа с Java Map, `send_document`, вспомогательная функция на верхнем уровне.

```
metainfo {
    id: "shareui_clibmini"
    name: "CactusLib Mini"
    version: "1.0.1"
    author: "@CactusPlugins | fork by @shareui"
    description: "Mini version of CactusLib"
    min_version: "12.2.10"
}

import base_plugin(BasePlugin, HookResult, HookStrategy)
import client_utils
import android_utils(log)
import markdown_utils(parse_markdown)
import ui.bulletin(BulletinHelper)
import ui.settings(Input)
import pathlib
import com.exteragram.messenger.plugins(PluginsController)
import org.telegram.messenger(ApplicationLoader)
import java.io(File)
import java.util(ArrayList, Arrays)
import org.telegram.tgnet(TLRPC)

fun getPythonEngine() {
    sus {
        val controller = PluginsController.getInstance()
        if not controller { return null }
        val engines = getattr(controller, "engines", null)
        if not engines { return null }
        return engines.get("python")
    } try {
        return null
    }
}

plugin CactusLibMini {
    fun on_load() {
        hook_send_message
    }

    fun on_send_message(account, params) {
        if not params.message { default }

        val msg = params.message.strip()
        val plfCmd = setting("plf_cmd", ".plf")
        val chelpCmd = setting("chelp_cmd", ".chelp")

        if msg.startswith(plfCmd) {
            if len(msg.split()) != 2 {
                BulletinHelper.show_info("Usage: $plfCmd <plugin_id>")
                cancel
            }
            val pluginId = msg.split()[1]
            sus {
                val plp = PluginsController.getInstance().getPluginPath(pluginId)
                if not plp or not pathlib.Path(plp).exists() {
                    BulletinHelper.show_info("Plugin not found: $pluginId")
                    cancel
                }
                val pl = PluginsController.getInstance().plugins.get(pluginId)
                val pluginVersion = pl.getVersion() or "1.0.0"
                val dir = File(ApplicationLoader.applicationContext.getExternalCacheDir(), "cactuslib_temp")
                if not dir.exists() { dir.mkdirs() }
                val file = File(dir, "${pluginId}-${pluginVersion}.plugin")
                sus {
                    open(file.getAbsolutePath(), "wb").write(open(plp, "rb").read())
                } try e {
                    log("copy failed: ${e}")
                    cancel
                }
                client_utils.send_document(params.peer, file.getAbsolutePath(), pl.getName())
                cancel
            } try e {
                BulletinHelper.show_info("Error while sending plugin file")
                log("${e}")
                cancel
            }
        }

        if msg.startswith(chelpCmd) {
            sus {
                val emojiOn = setting("emoji_enabled", "5776375003280838798")
                val emojiOff = setting("emoji_disabled", "5778527486270770928")
                val pls = PluginsController.getInstance().plugins
                var lines = []
                var enabled = 0
                var disabled = 0

                for pluginId, pl in zip(list(pls.keySet().toArray()), list(pls.values().toArray())) {
                    val isEnabled = pl.isEnabled()
                    var state = "[❌]($emojiOff)"
                    if isEnabled {
                        state = "[✅]($emojiOn)"
                        enabled = enabled + 1
                    } else {
                        disabled = disabled + 1
                    }
                    lines.append("[${pl.getVersion() or '-'}] $state *${pl.getName()}* (`$pluginId`)")
                }
                lines.append("\n${len(lines)} plugins, $enabled enabled, $disabled disabled.")

                val x = parse_markdown(lines.join("\n"))
                params.message = x.message

                val blockquote = TLRPC.TL_messageEntityBlockquote()
                blockquote.collapsed = true
                blockquote.offset = 0
                blockquote.length = int(len(x.message.encode(encoding="utf_16_le")) / 2)

                val ents = x.entities.map((e) -> e.to_tlrpc_object())
                params.entities = ArrayList(Arrays.asList([blockquote] + ents))
                modify params
            } try e {
                log("chelp error: ${e}")
                cancel
            }
        }

        default
    }
}

settings {
    input "plf_cmd" {
        text: "Send plugin file command"
        default: ".plf"
    }
    input "chelp_cmd" {
        text: "Plugin list command"
        default: ".chelp"
    }
    input "emoji_enabled" {
        text: "Enabled emoji ID"
        default: "5776375003280838798"
    }
    input "emoji_disabled" {
        text: "Disabled emoji ID"
        default: "5778527486270770928"
    }
}
```

---

## No More MusicPlayer — Xposed без Java-типов

Скрывает карточку плеера в профиле через хук на конструктор и метод `set`.

**Что демонстрирует:** `method_hook`, `after`, `hook_all_methods`, `param.thisObject`, работа с Android View через Java, `find_class` с проверкой на `null`.

```
metainfo {
    id: "no_music_player"
    name: "No More MusicPlayer"
    version: "1.0.0"
    author: "you"
    description: "Hides the now playing card"
    min_version: "12.1.0"
}

import base_plugin(BasePlugin, HookResult, HookStrategy, MethodHook)
import hook_utils(find_class)

val VIEW_GONE = 8

plugin NoMusicPlayer {
    method_hook ConstructorHook {
        fun after(param) {
            sus {
                val card = param.thisObject
                card.setVisibility(VIEW_GONE)
                val lp = card.getLayoutParams()
                if lp != null {
                    lp.height = 0
                    lp.topMargin = 0
                    lp.bottomMargin = 0
                    card.setLayoutParams(lp)
                }
            } try {
                // игнорируем ошибки — карточка может не существовать
            }
        }
    }

    method_hook SetHook {
        fun after(param) {
            sus {
                val data = param.args[0]
                if data == null { return }
                if data.getNowPlayingDTO().getPlatform() != "TELEGRAM" { return }
                val card = param.thisObject
                card.setVisibility(VIEW_GONE)
                val lp = card.getLayoutParams()
                if lp != null {
                    lp.height = 0
                    lp.topMargin = 0
                    lp.bottomMargin = 0
                    card.setLayoutParams(lp)
                }
                card.requestLayout()
            } try {
                // игнорируем
            }
        }
    }

    fun on_load() {
        val concreteClass = find_class("org.telegram.ui.ProfileActivity$ListAdapter$5")
        val abstractClass = find_class("com.exteragram.messenger.nowplaying.ui.components.NowPlayingCard")

        if concreteClass == null or abstractClass == null {
            log("class not found")
            return
        }

        sus {
            val hooks = hook_all_methods(concreteClass, "<init>", ConstructorHook)
            log("hooked constructor: ${len(hooks)} method(s)")
        } try e {
            log("constructor hook failed: ${e.message}")
        }

        sus {
            val hooks = hook_all_methods(abstractClass, "set", SetHook)
            log("hooked set: ${len(hooks)} method(s)")
        } try e {
            log("set hook failed: ${e.message}")
        }
    }
}
```
