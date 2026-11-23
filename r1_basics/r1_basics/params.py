"""Deklaracja parametrów liczbowych odpornych na `-p max_v:=1` (int zamiast float)."""
from rcl_interfaces.msg import ParameterDescriptor


def declare_float(node, name, default):
    """Parametr zmiennoprzecinkowy, który przyjmie też liczbę całkowitą z linii poleceń.

    Bez dynamic_typing `ros2 run ... -p max_v:=1` kończy się błędem typu (INTEGER zamiast DOUBLE).
    """
    value = node.declare_parameter(name, default, ParameterDescriptor(dynamic_typing=True)).value
    return float(value)
