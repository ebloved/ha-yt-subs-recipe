"""Config flow for YT Subs → Recipe."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_MODELS,
    CONF_PROXY,
    DEFAULT_MODELS,
)


class YtSubsRecipeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for YT Subs → Recipe."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_API_KEY):
                errors["base"] = "api_key_required"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="YT Subs → Recipe",
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_MODELS, default=DEFAULT_MODELS): str,
                vol.Optional(CONF_PROXY, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return options flow for this handler."""
        return YtSubsRecipeOptionsFlow(config_entry)


class YtSubsRecipeOptionsFlow(config_entries.OptionsFlow):
    """Handle options for YT Subs → Recipe."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_API_KEY,
                    default=current.get(CONF_API_KEY, ""),
                ): str,
                vol.Optional(
                    CONF_MODELS,
                    default=current.get(CONF_MODELS, DEFAULT_MODELS),
                ): str,
                vol.Optional(
                    CONF_PROXY,
                    default=current.get(CONF_PROXY, ""),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)