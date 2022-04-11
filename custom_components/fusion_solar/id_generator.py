"""Helper class to create ids from FusionSolarAPI credentials"""

import hashlib

from fusion_solar_py.client import FusionSolarClient

from .const import CURRENT_POWER, DAILY_ENERGY


def create_id_hash(client: FusionSolarClient, measurement: None) -> str:
    """Create a hash from the FusionSolarClient - and the specified measurement"""
    m = hashlib.sha256()
    m.update(client._user.encode())
    m.update(client._password.encode())

    digest = m.hexdigest()

    if measurement == "current_power_kw":
        digest = digest + CURRENT_POWER
    elif measurement == "total_power_today_kwh":
        digest = digest + DAILY_ENERGY
    else:
        digest = digest + "-" + measurement

    return digest
