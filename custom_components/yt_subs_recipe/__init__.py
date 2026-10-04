"""The YT Subs → Recipe integration."""

from __future__ import annotations

import asyncio
import glob
import logging
import re
import uuid
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_JOB_ID,
    ATTR_TEXT,
    ATTR_URL,
    CONF_API_KEY,
    CONF_MODELS,
    CONF_PROXY,
    DEFAULT_MODELS,
    DOMAIN,
    SERVICE_DOWNLOAD_AND_GENERATE,
    SERVICE_DOWNLOAD_SUBS,
    SERVICE_GENERATE_RECIPE,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# In-memory кэш текстов субтитров по job_id
_JOBS: dict[str, str] = {}

FRONTEND_URL = "/yt_subs_recipe/yt-subs-recipe-card.js"
FRONTEND_PATH = "custom_components/yt_subs_recipe/www/yt-subs-recipe-card.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve Lovelace card and register it automatically."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                FRONTEND_URL,
                hass.config.path(FRONTEND_PATH),
                cache_headers=False,
            )
        ]
    )

    hass.data.setdefault("frontend_extra_module_url", set())
    hass.data["frontend_extra_module_url"].add(FRONTEND_URL)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up YT Subs → Recipe from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"entry": entry}

    await _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


# ---------- Помощники ----------

def _get_config(hass: HomeAssistant) -> dict[str, Any]:
    """Возвращает текущую конфигурацию (data + options)."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        return {**entry.data, **entry.options}
    return {}


def clean_vtt_text(raw: str) -> str:
    """Убирает таймкоды, теги и дубли из VTT."""
    raw = re.sub(r"^WEBVTT.*?\n\n", "", raw, flags=re.DOTALL)
    raw = re.sub(r"\d{2}:\d{2}:\d{2}[.,]\d{3} --> .*?\n", "", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = re.sub(r"^[a-z-]+:.*$", "", raw, flags=re.MULTILINE)

    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    cleaned: list[str] = []
    for line in lines:
        if not cleaned or cleaned[-1] != line:
            cleaned.append(line)
    return " ".join(cleaned)


def _read_file_sync(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


async def _download_subs(hass: HomeAssistant, url: str) -> tuple[str, str]:
    """Скачивает субтитры через yt-dlp. Возвращает (job_id, текст)."""
    import yt_dlp

    job_id = uuid.uuid4().hex[:8]
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["ru.*", "en.*"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
        "outtmpl": f"/tmp/{job_id}_%(title)s.%(ext)s",
    }

    def _run() -> None:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    await hass.async_add_executor_job(_run)

    files = glob.glob(f"/tmp/{job_id}_*.vtt")
    text_parts = []
    for f in files:
        raw = await hass.async_add_executor_job(_read_file_sync, f)
        text_parts.append(clean_vtt_text(raw))

    if not text_parts:
        raise RuntimeError("Субтитры не найдены или не удалось скачать")

    return job_id, "\n\n".join(text_parts)


RECIPE_PROMPT = """Ты — редактор кулинарных рецептов.
Тебе дан текст из субтитров YouTube Shorts (возможно, с ошибками распознавания речи).
Оформи его как Markdown-рецепт с YAML front matter:
title, description, tags, servings, prep_time, cook_time, total_time,
ingredients (name/amount/unit), steps, notes.
Исправь очевидные ошибки распознавания. Не выдумывай данные, которых нет.
Верни ТОЛЬКО Markdown, без пояснений и без обрамляющих ```.

Текст субтитров:
{text}
"""


async def _call_gemini(
    hass: HomeAssistant,
    text: str,
    api_key: str,
    models: list[str],
    proxy: str | None = None,
) -> tuple[str, str]:
    """Вызывает Gemini с fallback по моделям. Возвращает (markdown, model)."""
    prompt = RECIPE_PROMPT.format(text=text)
    last_error: Exception | None = None

    async with aiohttp.ClientSession() as session:
        for model in models:
            for attempt in range(1, 4):
                try:
                    url = (
                        "https://generativelanguage.googleapis.com/v1beta/"
                        f"models/{model}:generateContent?key={api_key}"
                    )
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 2000,
                        },
                    }
                    kwargs: dict[str, Any] = {}
                    if proxy:
                        kwargs["proxy"] = proxy

                    async with session.post(url, json=payload, **kwargs) as resp:
                        if resp.status in (503, 429):
                            body = await resp.text()
                            raise RuntimeError(f"{resp.status}: {body[:200]}")
                        resp.raise_for_status()
                        data = await resp.json()

                    markdown = (
                        data["candidates"][0]["content"]["parts"][0]["text"]
                    ).strip()
                    if markdown.startswith("```"):
                        markdown = re.sub(r"^```[a-zA-Z]*\n", "", markdown)
                        markdown = re.sub(r"\n```$", "", markdown)
                    return markdown.strip(), model

                except Exception as e:  # noqa: BLE001
                    last_error = e
                    _LOGGER.warning(
                        "Gemini model=%s attempt=%s failed: %s", model, attempt, e
                    )
                    if attempt < 3:
                        await asyncio.sleep(2**attempt)

    raise RuntimeError(f"Все модели недоступны: {last_error}")


# ---------- Сервисы ----------

async def _async_register_services(hass: HomeAssistant) -> None:
    """Регистрирует сервисы интеграции."""

    async def handle_download_subs(call: ServiceCall) -> dict:
        url = call.data[ATTR_URL]
        job_id, text = await _download_subs(hass, url)
        _JOBS[job_id] = text
        return {"job_id": job_id, "text": text}

    async def handle_generate_recipe(call: ServiceCall) -> dict:
        config = _get_config(hass)
        api_key = config.get(CONF_API_KEY)
        models = [
            m.strip()
            for m in config.get(CONF_MODELS, DEFAULT_MODELS).split(",")
            if m.strip()
        ]
        proxy = config.get(CONF_PROXY) or None

        text = call.data.get(ATTR_TEXT) or _JOBS.get(call.data.get(ATTR_JOB_ID, ""))
        if not text:
            raise vol.Invalid("Нужно указать text или job_id")

        markdown, used_model = await _call_gemini(hass, text, api_key, models, proxy)
        return {"markdown": markdown, "model": used_model}

    async def handle_download_and_generate(call: ServiceCall) -> dict:
        url = call.data[ATTR_URL]
        job_id, text = await _download_subs(hass, url)
        _JOBS[job_id] = text

        config = _get_config(hass)
        api_key = config.get(CONF_API_KEY)
        models = [
            m.strip()
            for m in config.get(CONF_MODELS, DEFAULT_MODELS).split(",")
            if m.strip()
        ]
        proxy = config.get(CONF_PROXY) or None

        markdown, used_model = await _call_gemini(hass, text, api_key, models, proxy)
        return {"job_id": job_id, "markdown": markdown, "model": used_model}

    hass.services.async_register(
        DOMAIN,
        SERVICE_DOWNLOAD_SUBS,
        handle_download_subs,
        schema=vol.Schema({vol.Required(ATTR_URL): cv.url}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_RECIPE,
        handle_generate_recipe,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_TEXT): cv.string,
                vol.Optional(ATTR_JOB_ID): cv.string,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DOWNLOAD_AND_GENERATE,
        handle_download_and_generate,
        schema=vol.Schema({vol.Required(ATTR_URL): cv.url}),
        supports_response=SupportsResponse.ONLY,
    )