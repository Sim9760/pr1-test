from . import builtin, control, input, local_notification, rotary_valve, timer


units = {
  unit.namespace: unit for unit in [builtin, control, input, local_notification, rotary_valve, timer]
}

__all__ = ["units"]
