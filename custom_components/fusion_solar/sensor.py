"""The update coordinator for the FusionSolar integration"""

from collections.abc import Callable
from dataclasses import dataclass
import datetime
import logging

from homeassistant.components.sensor import (
    SensorStateClass,
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENERGY_KILO_WATT_HOUR, POWER_KILO_WATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, callback

from .const import COORDINATOR, DOMAIN
from .update_coordinator import FusionSolarCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the FRITZ!SmartHome light from ConfigEntry."""
    entities: list[FusionSolarSensor] = []
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    if "total" in coordinator.data:
        entities.append(
            FusionSolarSensor(coordinator, SENSOR_TYPES["total-current_power_kw"])
        )
        entities.append(
            FusionSolarSensor(coordinator, SENSOR_TYPES["total-power_today_kwh"])
        )

    if "plants" in coordinator.data:
        for plant_id in coordinator.data["plants"].keys():
            entities.append(
                FusionSolarSensor(coordinator, SENSOR_TYPES["power_kwh"], plant_id)
            )

    async_add_entities(entities)


@dataclass
class FusionSolarEntityDescription(SensorEntityDescription):
    """Entity description of fusion solar entities"""

    plant_type: str = None
    last_reset_fn: Callable = None


# URL to image: "https://eu5.fusionsolar.huawei.com/pvmswebsite/images/sm/login-logo.png"


class FusionSolarSensor(CoordinatorEntity, SensorEntity):
    """Reports the current power production reported through the FusionSolar API"""

    entity_description: FusionSolarEntityDescription

    def __init__(
        self,
        coordinator: FusionSolarCoordinator,
        description: FusionSolarEntityDescription,
        plant_id: str = None,
    ) -> None:
        """Initialize a new FusionSolarSensor

        :param coordinator: The coordinator to use for updates
        :type coordinator: FusionSolarCoordinator
        :param description: The description object for this sensor.
        :type: FusionSolarEntityDescription
        :param plant_id: The plant's id. Only relevant for actual plants, defaults to None
        :type plant_id: str, optional
        """
        # pass the coordinator to the base class
        super().__init__(coordinator)

        self.entity_description = description
        self.plant_id = plant_id

        self._attr_native_value = self._get_data()

        # initialize a last reset with midnight of today
        self._last_value = self._attr_native_value
        current_date = datetime.datetime.now()

        self._last_reset = datetime.datetime(
            year=current_date.year,
            month=current_date.month,
            day=current_date.day,
            hour=0,
            minute=0,
        )

    def _get_data(self) -> float:
        """Retrieve the current sensor value from the coordinator

        :return: The current value
        :rtype: float
        """
        if self.entity_description.plant_type == "total":
            value_keys = self.entity_description.key.split("-")
            value = self.coordinator.data[value_keys[0]][value_keys[1]]
        else:
            value = self.coordinator.data["plants"][self.plant_id][
                self.entity_description.key
            ]["value"]

        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        new_value = self._get_data()

        # if the new value is lower than the previous one,
        # expect that there might have been a reset
        _LOGGER.debug(
            "Updating value. last_value = %s, new_value = %s",
            str(self._last_value),
            str(new_value),
        )

        if new_value is not None and self._last_value is not None:
            if new_value < self._last_value:
                self._last_reset = datetime.datetime.now()

        # this is used in order to only save proper readings
        if new_value is not None:
            self._last_value = new_value

        self._attr_native_value = new_value

        # tell HA that the value changed
        self.async_write_ha_state()

    @property
    def last_reset(self) -> datetime:
        """Last reset as defined by the last_reset_fn"""
        if self.entity_description.last_reset_fn:
            return self.entity_description.last_reset_fn(self)

        return None


def last_reset_data(sensor_object: FusionSolarSensor) -> datetime:
    """Returns the last reset date based on the received data

    :param sensor_object: The sensor object calling the function
    :type sensor_object: FusionSolarSensor
    :return: The last reset data
    :rtype: datetime
    """
    last_update_str = sensor_object.coordinator.data["plants"][sensor_object.plant_id][
        sensor_object.entity_description.key
    ]["time"]

    return datetime.datetime.strptime(last_update_str, "%Y-%m-%d %H:%M")


def last_reset_self(sensor_object: FusionSolarSensor) -> datetime:
    """Return the last_reset stored as part of the object

    :param self: The FusionSolarObject calling the function
    :type: sensobr_object: FusionSolarSensor
    :return: The last_reset stored with the object
    :rtype: datetime
    """
    return sensor_object._last_reset


SENSOR_TYPES = {
    "total-current_power_kw": FusionSolarEntityDescription(
        key="total-current_power_kw",
        plant_type="total",
        name="Total Power - Now",
        icon="mdi:solar-panel",
        entity_category="diagnostic",
        native_unit_of_measurement=POWER_KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "total-power_today_kwh": FusionSolarEntityDescription(
        key="total-power_today_kwh",
        plant_type="total",
        name="Total Energy - Today",
        icon="mdi:solar-panel",
        entity_category="diagnostic",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        last_reset_fn=last_reset_self,
    ),
    "power_kwh": FusionSolarEntityDescription(
        key="productPower",
        plant_type="plant",
        name="Power",
        icon="mdi:solar-panel",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        # last_reset_fn=last_reset_data,
    ),
}
