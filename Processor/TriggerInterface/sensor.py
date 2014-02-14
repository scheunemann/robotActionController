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
            self._sensorInt = SensorInterface.getSensorInterface(sensor)

    def getActive(self):
        value = self._sensorInt.getCurrentValue()
        sensorValue = self._trigger.sensorValue
        comparison = self._trigger.comparison  # >, >=, <, <=, ==
        if comparison == '<':
            return value < sensorValue
        elif comparison == '<=':
            return value <= sensorValue
        elif comparison == '==':
            return value == sensorValue
        elif comparison == '>=':
            return value >= sensorValue
        elif comparison == '>':
            return value > sensorValue
        else:
            self._logger.warn("Unknown comparison type '%s' for trigger %s, default to ==" % comparison, self._trigger.name)
            return value == sensorValue
