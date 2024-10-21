"""Sensors for the MySkoda integration."""

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]

from myskoda.models import charging
from myskoda.models.charging import Charging, ChargingStatus
from myskoda.models.info import CapabilityId

from .const import COORDINATORS, DOMAIN
from .entity import MySkodaEntity
from .utils import add_supported_entities


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    _discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    add_supported_entities(
        available_entities=[
            BatteryPercentage,
            ChargeType,
            ChargingPower,
            ChargingState,
            LastUpdated,
            MainRender,
            Mileage,
            RemainingChargingTime,
            RemainingDistance,
            SoftwareVersion,
            TargetBatteryPercentage,
        ],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaSensor(MySkodaEntity, SensorEntity):
    pass


class SoftwareVersion(MySkodaSensor):
    """Current software version of a vehicle."""

    entity_description = SensorEntityDescription(
        key="software_version",
        name="Software Version",
        icon="mdi:update",
        translation_key="software_version",
    )

    @property
    def native_value(self):  # noqa: D102
        return self.vehicle.info.software_version


class ChargingSensor(MySkodaSensor):
    def _charging(self) -> Charging | None:
        if charging := self.vehicle.charging:
            return charging

    def _status(self) -> ChargingStatus | None:
        if charging := self._charging():
            if status := charging.status:
                return status

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]


class BatteryPercentage(ChargingSensor):
    """Battery charging state in percent."""

    entity_description = SensorEntityDescription(
        key="battery_percentage",
        name="Battery Percentage",
        icon="mdi:battery",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        translation_key="battery_percentage",
    )

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if status := self._status():
            return status.battery.state_of_charge_in_percent

    @property
    def icon(self) -> str:  # noqa: D102
        if not (status := self._status()):
            return "mdi:battery-outline"

        if status.battery.state_of_charge_in_percent >= 95:
            suffix = "100"
        elif status.battery.state_of_charge_in_percent >= 85:
            suffix = "90"
        elif status.battery.state_of_charge_in_percent >= 75:
            suffix = "80"
        elif status.battery.state_of_charge_in_percent >= 65:
            suffix = "70"
        elif status.battery.state_of_charge_in_percent >= 55:
            suffix = "60"
        elif status.battery.state_of_charge_in_percent >= 45:
            suffix = "50"
        elif status.battery.state_of_charge_in_percent >= 35:
            suffix = "40"
        elif status.battery.state_of_charge_in_percent >= 25:
            suffix = "30"
        elif status.battery.state_of_charge_in_percent >= 15:
            suffix = "20"
        elif status.battery.state_of_charge_in_percent >= 5:
            suffix = "10"
        else:
            suffix = "outline"

        if status.state != charging.ChargingState.CONNECT_CABLE:
            return f"mdi:battery-charging-{suffix}"
        if suffix == "100":
            return "mdi:battery"
        return f"mdi:battery-{suffix}"


class ChargingPower(ChargingSensor):
    """How fast the car is charging in kW."""

    entity_description = SensorEntityDescription(
        key="charging_power",
        name="Charging Power",
        icon="mdi:lightning-bolt",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        translation_key="charging_power",
    )

    @property
    def native_value(self) -> float | None:  # noqa: D102
        if status := self._status():
            return status.charge_power_in_kw


class RemainingDistance(ChargingSensor):
    """Estimated range of an electric vehicle in km."""

    entity_description = SensorEntityDescription(
        key="range",
        name="Range",
        icon="mdi:speedometer",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        translation_key="range",
    )

    @property
    def native_value(self) -> int | float | None:  # noqa: D102
        if status := self._status():
            return status.battery.remaining_cruising_range_in_meters / 1000


class TargetBatteryPercentage(ChargingSensor):
    """Charging target of the EV's battery in percent."""

    entity_description = SensorEntityDescription(
        key="target_battery_percentage",
        name="Target Battery Percentage",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
        device_class=SensorDeviceClass.BATTERY,
        translation_key="target_battery_percentage",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if charging := self._charging():
            return charging.settings.target_state_of_charge_in_percent


class Mileage(MySkodaSensor):
    """The vehicle's mileage (total kilometers driven)."""

    entity_description = SensorEntityDescription(
        key="milage",
        name="Milage",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        icon="mdi:counter",
        device_class=SensorDeviceClass.DISTANCE,
        translation_key="milage",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if health := self.vehicle.health:
            return health.mileage_in_km

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.VEHICLE_HEALTH_INSPECTION]


class InspectionInterval(MySkodaSensor):
    """The number of days before next inspection."""

    entity_description = SensorEntityDescription(
        key="inspection",
        name="Inspection",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
        icon="mdi:car-wrench",
        translation_key="inspection",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if maintenance_report := self.vehicle.maintenance.maintenance_report:
            return maintenance_report.inspection_due_in_days

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.VEHICLE_HEALTH_INSPECTION]


class ChargeType(ChargingSensor):
    """How the vehicle is being charged (AC/DC)."""

    entity_description = SensorEntityDescription(
        key="charge_type",
        name="Charge Type",
        translation_key="charge_type",
    )

    @property
    def native_value(self) -> str | None:  # noqa: D102
        if status := self._status():
            return str(status.charge_type).lower()

    @property
    def icon(self) -> str:  # noqa: D102
        if status := self._status():
            if status.charge_type == "DC":
                return "mdi:ev-plug-ccs2"

        return "mdi:ev-plug-type2"


class ChargingState(ChargingSensor):
    """Current state of charging (ready, charging, conserving, ...)."""

    entity_description = SensorEntityDescription(
        key="charging_state",
        name="Charging State",
        device_class=SensorDeviceClass.ENUM,
        translation_key="charging_state",
    )

    # lower_snake_case for translations
    _attr_options = [
        "connect_cable",
        "ready_for_charging",
        "conserving",
        "charging",
    ]

    @property
    def native_value(self) -> str | None:  # noqa: D102
        if status := self._status():
            if status.state:
                return str(status.state).lower()

    @property
    def icon(self) -> str:  # noqa: D102
        if status := self._status():
            if status.state == charging.ChargingState.CONNECT_CABLE:
                return "mdi:power-plug-off"
            if status.state == charging.ChargingState.CHARGING:
                return "mdi:power-plug-battery"
        return "mdi:power-plug"


class RemainingChargingTime(ChargingSensor):
    """Estimation on when the vehicle will be fully charged."""

    entity_description = SensorEntityDescription(
        key="remaining_charging_time",
        name="Remaining Charging Time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer",
        translation_key="remaining_charging_time",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if status := self._status():
            return status.remaining_time_to_fully_charged_in_minutes


class LastUpdated(MySkodaSensor):
    """Timestamp of when the car has sent the last update to the MySkoda server."""

    entity_description = SensorEntityDescription(
        key="car_captured",
        name="Last Updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock",
        translation_key="car_captured",
    )

    @property
    def native_value(self) -> datetime | None:  # noqa: D102
        if status := self.vehicle.status:
            return status.car_captured_timestamp

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE]


class MainRender(MySkodaSensor):
    """URL of the main image render of the vehicle."""

    entity_description = SensorEntityDescription(
        key="render_url_main",
        name="Main Render URL",
        icon="mdi:file-image",
        translation_key="render_url_main",
    )

    @property
    def native_value(self):  # noqa: D102
        return self.get_renders().get("main")
