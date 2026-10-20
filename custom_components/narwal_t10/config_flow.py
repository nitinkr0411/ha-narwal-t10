"""Config flow for the Narwal T10 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .ha_const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_EMAIL,
    CONF_MACHINE_ID,
    CONF_PASSWORD,
    CONF_REGION,
    DOMAIN,
)
from .narwal_client import NarwalAuthError, NarwalCloud, NarwalCloudError
from .narwal_client.const import API_HOSTS

_LOGGER = logging.getLogger(__name__)

_LOGIN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_REGION, default="us"): vol.In(sorted(API_HOSTS)),
    }
)


class NarwalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step flow: credentials, then pick the discovered robot."""

    VERSION = 1

    def __init__(self) -> None:
        self._cloud: NarwalCloud | None = None
        self._login: dict[str, Any] = {}
        self._robots: list = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            cloud = NarwalCloud(async_get_clientsession(self.hass), region=user_input[CONF_REGION])
            try:
                await cloud.login(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
                robots = await cloud.get_robots()
            except NarwalAuthError:
                errors["base"] = "invalid_auth"
            except NarwalCloudError:
                errors["base"] = "cannot_connect"
            else:
                if not robots:
                    errors["base"] = "no_robots"
                else:
                    self._cloud = cloud
                    self._login = dict(user_input)
                    self._robots = robots
                    if len(robots) == 1:
                        return await self._create(robots[0])
                    return await self.async_step_device()
        return self.async_show_form(step_id="user", data_schema=_LOGIN_SCHEMA, errors=errors)

    async def async_step_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            chosen = next(r for r in self._robots if r.device_id == user_input[CONF_DEVICE_ID])
            return await self._create(chosen)
        choices = {r.device_id: f"{r.name} ({r.device_id})" for r in self._robots}
        schema = vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(choices)})
        return self.async_show_form(step_id="device", data_schema=schema)

    async def _create(self, robot) -> ConfigFlowResult:
        await self.async_set_unique_id(robot.device_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=robot.name or f"Narwal T10 {robot.device_id}",
            data={
                CONF_EMAIL: self._login[CONF_EMAIL],
                CONF_PASSWORD: self._login[CONF_PASSWORD],
                CONF_REGION: self._login[CONF_REGION],
                CONF_DEVICE_ID: robot.device_id,
                CONF_MACHINE_ID: robot.machine_id,
                CONF_DEVICE_NAME: robot.name,
            },
        )
