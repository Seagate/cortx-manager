from ipaddress import ip_address
from typing import Any, Dict, Optional
# Removed package netifaces from csm
from netifaces import AF_LINK, AF_INET, ifaddresses, interfaces
from csm.core.data.models.usl import NetIface


def _get_ifaddresses_items(iface: str) -> Dict[str, Any]:
    return {
        k: v for k, v in ifaddresses(iface).items() if k in (AF_LINK, AF_INET)
    }


def _search_interface_by_ipv4_addr(addr: str) -> Optional[str]:
    for iface in interfaces():
        details = _get_ifaddresses_items(iface)
        for inet in details.get(AF_INET, ()):
            if inet.get('addr') == addr:
                return iface
    return None


def get_interface_details(addr: str) -> NetIface:
    # Validate IP address
    try:
        ip_address(addr)
    except ValueError as e:
        raise ValueError('Invalid IP address') from e
    # Initialize dict
    args: Dict[str, Any] = dict()
    # Fill basic info
    alias_name = _search_interface_by_ipv4_addr(addr)
    if alias_name is None:
        raise RuntimeError(f'IP address {addr} is not currently assigned to an interface')
    iface_name = next(iter(alias_name.split(':')))
    args['name'] = iface_name
    # Get interface details based on name
    try:
        alias_details = _get_ifaddresses_items(alias_name)
        iface_details = _get_ifaddresses_items(iface_name)
    except ValueError as e:
        raise RuntimeError(f'Could not obtain interface details for address {addr}') from e
    # Fill link info
    # FIXME derive ``isActive``, ``isLoopback``, ``type`` from link info
    args['is_active'] = True
    args['is_loopback'] = ip_address(addr).is_loopback
    args['iface_type'] = 'loopback' if args['is_loopback'] else 'ether'
    if (
        AF_LINK in iface_details and
        len(iface_details[AF_LINK]) > 0 and
        'addr' in iface_details[AF_LINK][0]
    ):
        args['mac_address'] = iface_details[AF_LINK][0]['addr']
    # Fill inet info
    for inet in alias_details.get(AF_INET, ()):
        if inet.get('addr') != addr:
            pass
        if 'addr' in inet:
            args['ipv4'] = inet['addr']
        if 'netmask' in inet:
            args['netmask'] = inet['netmask']
        if 'broadcast' in inet:
            args['broadcast'] = inet['broadcast']
    # Check for mandatory fields
    try:
        o = NetIface.instantiate(**args)
    except TypeError as e:
        raise ValueError(f'Could not build USL network interface model details for {addr}') from e
    return o
