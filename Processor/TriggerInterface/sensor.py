from triggerInterface import TriggerInterface
from Processor.SensorInterface import SensorInterface


class SensorTrigger(TriggerInterface):

    # trigger value >
    # trigger value <
    # trigger value =
    def __init__(self, trigger):
        super(SensorTrigger, self).__init__(trigger)
        if trigger.sensorName:
            sensor = self._getSensor(trigger.sensorName)
            self._onState = sensor.onState
            self._sensorInt = SensorInterface.getSensorInterface(sensor)

    def getActive(self):
        # Value is used in eval functions
        value = self._sensorInt.getCurrentValue()
        sensorValue = self._trigger.sensorValue
        if sensorValue.startswith('eval::'):
            if not self._onState:
                self._logger.critical("Unknown sensor eval: %s" % sensorValue[6:])
                return None
            isOn = eval(self._onState)
            if sensorValue[6:] == 'off':
                return not isOn
            elif sensorValue[6:] == 'on':
                return isOn
            else:
                self._logger.critical("Unknown sensor eval: %s" % sensorValue[6:])
                return None
        else:
            return eval('value' + sensorValue)
