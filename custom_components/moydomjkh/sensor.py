"""Platform for sensor integration."""
import logging
from datetime import timedelta

import async_timeout
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity
from moydomjkh.exceptions import InvalidSession, SessionException

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the moydomjkh sensor entry."""

    api = hass.data[DOMAIN][entry.entry_id]
    coordinator = MoyDomJKHSensorCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    entities = []
    for account in coordinator.data['accounts'].values():
        entities.append(MoyDomJKHBalanceSensor(coordinator, account))
        for meter in account['meters'].values():
            entities.append(MoyDomJKHUtilitySensor(coordinator, meter))

    async_add_entities(entities, update_before_add=True)


class MoyDomJKHSensorCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api):
        super().__init__(hass, _LOGGER, name="MoyDomJKHSensor", update_interval=timedelta(days=1))
        self.api = api

    def fetch_data(self):
        return self.api.to_json(3)

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(10):
                return await self.hass.async_add_executor_job(self.fetch_data)
        except InvalidSession as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except SessionException as err:
            raise UpdateFailed(f"Error communicating with API: {err}")


class MoyDomJKHBalanceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_icon = 'mdi:currency-rub'
    _attr_native_unit_of_measurement = 'руб'
    _attr_device_class = SensorDeviceClass.MONETARY

    def __init__(self, coordinator: MoyDomJKHSensorCoordinator, account: dict):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = account['account_name']
        self._attr_unique_id = account['account_id']
        self._attr_extra_state_attributes = {'address': account['address'],
                                             'area': account['area'],
                                             'company_name': account['company_name'],
                                             'account_id': account['account_id']}
        self._attr_native_value = account['balance']

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        account = self.coordinator.data['accounts'].get(self._attr_unique_id)
        self._attr_available = False
        if account:
            self._attr_available = True
            self._attr_native_value = account['balance']

        self.async_write_ha_state()


class MoyDomJKHUtilitySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_icon = 'mdi:gauge'

    # _attr_native_unit_of_measurement = 'руб'
    # _attr_device_class = SensorDeviceClass.

    def __init__(self, coordinator, meter):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = meter['name']
        self._attr_unique_id = meter['meter_id']
        ids = meter['meter_id'].split('-')
        self._account_id = f'{ids[0]}-{ids[1]}'
        self._attr_extra_state_attributes = {'serial_number': meter['serial_number'],
                                             'next_check_date': meter['next_check_date'],
                                             'meter_id': meter['meter_id']}
        self._attr_native_value = meter['value']

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = False
        account = self.coordinator.data['accounts'].get(self._account_id)
        if account:
            meter = account['meters'].get(self._attr_unique_id)
            if meter:
                self._attr_available = True
                self._attr_native_value = meter['value']

                self._attr_extra_state_attributes['serial_number'] = meter['serial_number']
                self._attr_extra_state_attributes['next_check_date'] = meter['next_check_date']
                self._attr_extra_state_attributes['meter_id'] = meter['meter_id']
        self.async_write_ha_state()
