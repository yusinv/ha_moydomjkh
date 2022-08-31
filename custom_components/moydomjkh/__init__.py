import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from moydomjkh import Session, User, Account, Meter, SessionException

from .const import *


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = User(
        Session(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    def submit_utility_usage(call):
        try:
            meter_id = call.data[METER]
            if not re.match("[0-9]+-[0-9]+-[0-9]+", meter_id):
                hass.bus.fire("submit_utility_usage_failed", {'msg': 'Meter id should have *-*-* format'})
                return
            ids = meter_id.split('-')
            api: User = hass.data[DOMAIN][entry.entry_id]
            account: Account = api.accounts.get(f'{ids[0]}-{ids[1]}')
            if not account:
                hass.bus.fire("submit_utility_usage_failed", {'msg': f'Can not find meter with id:{meter_id}'})
                return
            meter: Meter = account.meters.get(meter_id)
            if not account:
                hass.bus.fire("submit_utility_usage_failed", {'msg': f'Can not find meter with id:{meter_id}'})
                return
            if call.data.get(VALUE):
                meter.upload_measure(call.data.get(VALUE))
            elif call.data.get(DELTA_VALUE):
                meter.upload_measure(float(meter.meter_info['5']['value']) + float(call.data.get(DELTA_VALUE)))
            else:
                hass.bus.fire("submit_utility_usage_failed", {'msg': f'{VALUE} or {DELTA_VALUE} must be filled'})
                return

            hass.bus.fire("submit_utility_usage_success", {'value': meter.value})

        except SessionException as e:
            hass.bus.fire("submit_utility_usage_failed", {'msg': f'{str(e)}'})

    async def async_submit_utility_usage(call):
        await hass.async_add_executor_job(submit_utility_usage, call)

    hass.services.async_register(DOMAIN, 'submit_utility_usage', async_submit_utility_usage)

    def generate_payment_url(call):
        try:
            api: User = hass.data[DOMAIN][entry.entry_id]
            account: Account = api.accounts.get(call.data[ACCOUNT])
            if not account:
                hass.bus.fire("generate_payment_url_failed", {'msg': f'Can not find account with id:{call.data[ACCOUNT]}'})
                return

            url = account.generate_payment_url(call.data.get(AMOUNT))
            hass.bus.fire("generate_payment_url_success", {'url': url})

        except SessionException as e:
            hass.bus.fire("generate_payment_url_failed", {'msg': f'{str(e)}'})

    async def async_generate_payment_url(call):
        await hass.async_add_executor_job(generate_payment_url, call)

    hass.services.async_register(DOMAIN, 'generate_payment_url', async_generate_payment_url)

    return True
