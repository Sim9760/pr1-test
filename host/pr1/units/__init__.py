from . import builtin, input, local_notification, rotary_valve, timer


units = {
  unit.namespace: unit for unit in [builtin, input, local_notification, rotary_valve, timer]
}

__all__ = ["units"]
