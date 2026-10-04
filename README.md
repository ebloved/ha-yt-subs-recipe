# YT Subs → Recipe

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/YOUR_USERNAME/ha-yt-subs-recipe/actions/workflows/validate.yml/badge.svg)](https://github.com/YOUR_USERNAME/ha-yt-subs-recipe/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Интеграция Home Assistant, которая скачивает субтитры YouTube Shorts через `yt-dlp` и генерирует кулинарный рецепт в Markdown с помощью Google Gemini.

## Возможности

- 🔗 **Скачивание субтитров** YouTube Shorts (автоматические и ручные треки) в VTT
- 🤖 **Генерация рецепта** в Markdown с YAML front matter через Google Gemini
- 🔁 **Автоматический fallback** между моделями Gemini при перегрузке (503/429)
- 🌐 **Опциональный HTTP-прокси** для запросов к Gemini API
- 🧩 **Lovelace-карта** для работы прямо из интерфейса Home Assistant
- ⚙️ **Настройка через UI** — Config Flow и Options Flow

## Установка

### Через HACS (рекомендуется)

1. Откройте **HACS → Integrations**.
2. Нажмите **⋮ → Custom repositories**.
3. Вставьте URL репозитория:
   ```
   https://github.com/YOUR_USERNAME/ha-yt-subs-recipe
   ```
4. Выберите категорию **Integration**, нажмите **Add**.
5. Найдите «YT Subs → Recipe» в HACS и нажмите **Download**.
6. Перезапустите Home Assistant.

### Вручную

1. Скачайте архив с репозиторием.
2. Скопируйте папку `custom_components/yt_subs_recipe/` в `<config>/custom_components/`.
3. Перезапустите Home Assistant.

## Настройка

1. Откройте **Settings → Devices & Services → Add Integration**.
2. Найдите **YT Subs → Recipe**.
3. Заполните поля:

| Поле | Описание | По умолчанию |
|---|---|---|
| **Gemini API Key** | API-ключ Google Gemini | — (обязательно) |
| **Модели** | Список моделей через запятую, по приоритету | `gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash` |
| **Proxy host** | HTTP(S)-прокси для запросов к Gemini (опционально) | — |

API-ключ можно получить на [Google AI Studio](https://aistudio.google.com/apikey).

Изменить настройки после установки: **Settings → Devices & Services → YT Subs → Recipe → Configure**.

## Lovelace-карта

После установки интеграции карта автоматически подключается во фронтенде. Добавьте её в дашборд:

```yaml
type: custom:yt-subs-recipe-card
title: Рецепт из Shorts
```

Карта появится в списке как **Custom: YT Subs → Recipe**.

### Что умеет карта

- Вставить ссылку на YouTube Shorts
- **Скачать и сгенерировать** — комбо-действие одной кнопкой
- **Только субтитры** — получить `job_id` без обращения к Gemini
- **Только рецепт** — если `job_id` уже есть
- **Скопировать** результат в буфер обмена
- **Скачать .md** файлом на компьютер
- Показать использованную модель Gemini

## Сервисы

### `yt_subs_recipe.download_subs`

Скачивает субтитры и возвращает `job_id` и `text`.

```yaml
service: yt_subs_recipe.download_subs
data:
  url: "https://youtube.com/shorts/VIDEO_ID"
response_variable: subs
```

### `yt_subs_recipe.generate_recipe`

Генерирует рецепт из текста субтитров или по `job_id`.

```yaml
service: yt_subs_recipe.generate_recipe
data:
  job_id: "{{ subs.job_id }}"
response_variable: recipe
```

Или напрямую с текстом:

```yaml
service: yt_subs_recipe.generate_recipe
data:
  text: "В этом видео я покажу, как приготовить..."
response_variable: recipe
```

### `yt_subs_recipe.download_and_generate`

Комбо-сервис — скачивает субтитры и сразу генерирует рецепт.

```yaml
service: yt_subs_recipe.download_and_generate
data:
  url: "https://youtube.com/shorts/VIDEO_ID"
response_variable: recipe
```

Во всех случаях результат доступен в `recipe.markdown`.

## Примеры автоматизаций

### Сохранить рецепт в файл

```yaml
automation:
  - alias: "Рецепт из Shorts в файл"
    trigger:
      - platform: state
        entity_id: input_button.get_recipe
    action:
      - service: yt_subs_recipe.download_and_generate
        data:
          url: "{{ states('input_text.shorts_url') }}"
        response_variable: recipe
      - service: notify.persistent_notification
        data:
          title: "Рецепт готов"
          message: "{{ recipe.markdown }}"
```

### Отправить в Telegram

```yaml
automation:
  - alias: "Рецепт в Telegram"
    trigger:
      - platform: state
        entity_id: input_button.get_recipe
    action:
      - service: yt_subs_recipe.download_and_generate
        data:
          url: "{{ states('input_text.shorts_url') }}"
        response_variable: recipe
      - service: telegram_bot.send_message
        data:
          message: "{{ recipe.markdown }}"
```

### Сохранить в input_text

```yaml
automation:
  - alias: "Рецепт в input_text"
    trigger:
      - platform: state
        entity_id: input_button.get_recipe
    action:
      - service: yt_subs_recipe.download_and_generate
        data:
          url: "{{ states('input_text.shorts_url') }}"
        response_variable: recipe
      - service: input_text.set_value
        target:
          entity_id: input_text.last_recipe
        data:
          value: "{{ recipe.markdown }}"
```

## Обход блокировок

### Gemini API

Если `generativelanguage.googleapis.com` недоступен напрямую (например, из России), укажите в настройках интеграции HTTP(S)-прокси:

```
http://proxy.example.com:8080
```

или

```
socks5://user:pass@proxy.example.com:1080
```

### YouTube

`yt-dlp` скачивает только субтитры и не требует авторизации для большинства публичных видео. Если YouTube блокирует IP:

- Используйте VPN на уровне роутера или хоста.
- Для сложных случаев лучше поднять отдельный прокси и направить HA через него.

## Требования

- Home Assistant **2026.8.0** или новее
- Python 3.12+
- `yt-dlp` устанавливается автоматически как зависимость интеграции
- `ffmpeg` **не требуется** — субтитры скачиваются сразу в VTT

## Troubleshooting

### Интеграция не появляется в HACS

Убедитесь, что репозиторий добавлен как **Custom repository** с категорией **Integration**, а не **Plugin**.

### Карта не появляется в списке

1. Проверьте **Developer Tools → Console** в браузере на ошибки JS.
2. Перезагрузите страницу с `Ctrl+Shift+R`.
3. Перезапустите HA.
4. Убедитесь, что `www/yt-subs-recipe-card.js` существует в `custom_components/yt_subs_recipe/`.

### Ошибка `api_key_required`

Не заполнено обязательное поле **Gemini API Key** при настройке. Откройте **Configure** и введите ключ.

### Ошибка `503 UNAVAILABLE` от Gemini

Модель перегружена. Интеграция автоматически пробует следующие модели из списка. Если все недоступны — увеличьте список в настройках.

### Ошибка `Все модели недоступны`

1. Проверьте правильность API-ключа.
2. Проверьте, что модели из списка существуют и доступны вашему аккаунту.
3. Если используете прокси — убедитесь, что он работает.

### Субтитры не найдены

Некоторые видео не имеют субтитров вообще. Проверьте на странице YouTube — если субтитров нет, `yt-dlp` их не скачает.

## Разработка

```bash
git clone https://github.com/YOUR_USERNAME/ha-yt-subs-recipe.git
cd ha-yt-subs-recipe

# Симлинк в конфиг HA для локальной разработки
ln -s "$(pwd)/custom_components/yt_subs_recipe" \
      /path/to/ha/config/custom_components/yt_subs_recipe
```

Для проверки перед коммитом:

```bash
# Синтаксис Python
python -m compileall custom_components/yt_subs_recipe

# Валидация HACS и hassfest запустятся автоматически через GitHub Actions
```

## Лицензия

[MIT](LICENSE)

## Благодарности

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — скачивание субтитров
- [Google Gemini](https://ai.google.dev/) — генерация рецептов
- [Home Assistant](https://www.home-assistant.io/) — платформа