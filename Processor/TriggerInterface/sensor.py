from triggerInterface import TriggerInterface
from Processor.SensorInterface import SensorInterface


class SensorTrigger(TriggerInterface):

    # trigger value >
    # trigger value <
    # trigger value =
    def __init__(self, trigger, robot, **kwargs):
        super(SensorTrigger, self).__init__(trigger, **kwargs)
        if trigger.sensorName:
            sensor = self._getSensor(trigger.sensorName, robot)
            if sensor:
                if not sensor.onStateComparison or sensor.onStateValue:
                    self._onState = None
                else:
                    self._onState = sensor.onStateComparison + sensor.onStateValue
                self._sensorInt = SensorInterface.getSensorInterface(sensor)
            else:
                raise ValueError('Unknown sensor %s on robot %s' % (trigger.sensorName, robot.name))

    def _getSensor(self, sensorName, robot):
        sensors = [s for s in robot.sensors if s.name == sensorName]
        return sensors[0] if sensors else None

    def getActive(self):
        # Value is used in eval functions
        value = self._sensorInt.getCurrentValue()
        sensorValue = self._trigger.sensorValue
        sensorCompare = self._trigger.comparison
        if sensorValue.startswith('eval::'):
            if not self._onState:
                self._logger.critical("Unknown sensor eval: %s" % sensorValue[6:])
                return None
            isOn = eval('value %s' % self._onState)
            if sensorValue[6:] == 'off':
                return not isOn
            elif sensorValue[6:] == 'on':
                return isOn
            else:
                self._logger.critical("Unknown sensor eval: %s" % sensorValue[6:])
                return None
        else:
            return eval('value %s%s' % (sensorCompare, sensorValue))
