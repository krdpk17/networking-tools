import pdb
import socket
import pyroute2
from pyroute2 import netlink
import six

_IP_VERSION_FAMILY_MAP = {4: socket.AF_INET, 6: socket.AF_INET6}

class NetworkNamespaceNotFound(RuntimeError):
    message = ("Network namespace %(netns_name)s could not be found.")

    def __init__(self, netns_name):
        super(NetworkNamespaceNotFound, self).__init__(
            self.message % {'netns_name': netns_name})


def make_serializable(value):
    """Make a pyroute2 object serializable

    This function converts 'netlink.nla_slot' object (key, value) in a list
    of two elements.
    """
    def _ensure_string(value):
        # NOTE(ralonsoh): once support for PY2 is dropped, the str()
        # conversion will be no needed and six.binary_type --> bytes.
        return (str(value.decode('utf-8'))
                if isinstance(value, six.binary_type) else value)

    if isinstance(value, list):
        return [make_serializable(item) for item in value]
    elif isinstance(value, netlink.nla_slot):
        return [value[0], make_serializable(value[1])]
    elif isinstance(value, netlink.nla_base) and six.PY3:
        return make_serializable(value.dump())
    elif isinstance(value, dict):
        return {_ensure_string(key): make_serializable(data)
                for key, data in value.items()}
    elif isinstance(value, tuple):
        return tuple(make_serializable(item) for item in value)
    return _ensure_string(value)


def get_iproute(namespace):
    # From iproute.py:
    # `IPRoute` -- RTNL API to the current network namespace
    # `NetNS` -- RTNL API to another network namespace
    if namespace:
        # do not try and create the namespace
        return pyroute2.NetNS(namespace, flags=0)
    else:
        return pyroute2.IPRoute()


def list_ip_rules(namespace, ip_version, match=None, **kwargs):
    """List all IP rules"""
    try:
        with get_iproute(namespace) as ip:
            rules = make_serializable(ip.get_rules(
                family=_IP_VERSION_FAMILY_MAP[ip_version],
                match=match, **kwargs))
            for rule in rules:
                rule['attrs'] = {
                    key: value for key, value
                    in ((item[0], item[1]) for item in rule['attrs'])}
            return rules

    except OSError as e:
        if e.errno == errno.ENOENT:
            raise NetworkNamespaceNotFound(netns_name=namespace)
        raise

def add_ip_rule(namespace, **kwargs):
    """Add a new IP rule"""
    try:
        with get_iproute(namespace) as ip:
            ip.rule('add', **kwargs)
    except netlink_exceptions.NetlinkError as e:
        if e.code == errno.EEXIST:
            return
        raise
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise NetworkNamespaceNotFound(netns_name=namespace)
        raise

rules = list_ip_rules(None,4)

print("{}".format(rules))
