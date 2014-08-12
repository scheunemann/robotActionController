from triggerInterface import TriggerInterface
from collections import namedtuple
import logging


class SensorTrigger(TriggerInterface):
    supportedClass = 'SensorTrigger'
    Runable = namedtuple('SensorTrigger', TriggerInterface.Runable._fields + ('sensorName', 'sensorValue', 'comparison', ))

    def __init__(self, trigger, robot, **kwargs):
        super(SensorTrigger, self).__init__(trigger, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)
        if trigger.sensorName:
            self._sensorInt = self._getSensor(trigger.sensorName, robot)
            if not self._sensorInt:
                raise ValueError('Unknown sensor %s on robot %s' % (trigger.sensorName, robot.name))

    def _getSensor(self, sensorName, robot):
        sensors = [s for s in robot.sensors if s.sensorName == sensorName]
        return sensors[0] if sensors else None

    @staticmethod
    def getRunable(trigger):
        if trigger.type == SensorTrigger.supportedClass:
            return SensorTrigger.Runable(trigger.name, trigger.id, trigger.type, trigger.sensorName, trigger.sensorValue, trigger.comparison)
        else:
            logger = logging.getLogger(SensorTrigger.__name__)
            logger.error("Trigger: %s has an unknown trigger type: %s" % (trigger.name, trigger.type))
            return None

    def getActive(self):
        # Value is used in eval functions
        value = self._sensorInt.getCurrentValue()
        sensorValue = self._trigger.sensorValue
        sensorCompare = self._trigger.comparison
        if sensorValue.startswith('eval::'):
            # sensorValue === eval::on || eval::off
            if not self._sensorInt.onState:
                self._logger.critical("Cannot eval:: sensor %s, no onState set" % self._trigger.sensorName)
                return None
            isOn = eval('%(value)s %(comp)s' % {'value': value, 'comp': self._sensorInt.onState})
            if sensorValue[6:] == 'off':
                return not isOn
            elif sensorValue[6:] == 'on':
                return isOn
            else:
                self._logger.critical("Unknown sensor eval: %s" % sensorValue[6:])
                return None
        else:
            return eval('%(value) %(comp)s %(compVal)s' % {'value': value, 'comp': sensorCompare, 'compVal': sensorValue})
