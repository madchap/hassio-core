"""The scrape component."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components.rest import RESOURCE_SCHEMA, create_rest_data_from_config
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_SCAN_INTERVAL,
    CONF_VALUE_TEMPLATE,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.template_entity import TEMPLATE_SENSOR_BASE_SCHEMA
from homeassistant.helpers.typing import ConfigType

from .const import CONF_INDEX, CONF_SELECT, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import ScrapeCoordinator

SENSOR_SCHEMA = vol.Schema(
    {
        **TEMPLATE_SENSOR_BASE_SCHEMA.schema,
        vol.Optional(CONF_ATTRIBUTE): cv.string,
        vol.Optional(CONF_INDEX, default=0): cv.positive_int,
        vol.Required(CONF_SELECT): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    }
)

COMBINED_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL): cv.time_period,
        **RESOURCE_SCHEMA,
        vol.Optional(SENSOR_DOMAIN): vol.All(
            cv.ensure_list, [vol.Schema(SENSOR_SCHEMA)]
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(DOMAIN): vol.All(cv.ensure_list, [COMBINED_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Scrape from yaml config."""
    scrape_config: list[ConfigType] | None
    if not (scrape_config := config.get(DOMAIN)):
        return True

    load_coroutines: list[Coroutine[Any, Any, None]] = []
    for resource_config in scrape_config:
        rest = create_rest_data_from_config(hass, resource_config)
        coordinator = ScrapeCoordinator(
            hass,
            rest,
            timedelta(
                seconds=resource_config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

        sensors: list[ConfigType] = resource_config.get(SENSOR_DOMAIN, [])
        if sensors:
            load_coroutines.append(
                discovery.async_load_platform(
                    hass,
                    Platform.SENSOR,
                    DOMAIN,
                    {"coordinator": coordinator, "configs": sensors},
                    config,
                )
            )

    if load_coroutines:
        await asyncio.gather(*load_coroutines)

    return True
