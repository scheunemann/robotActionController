from datetime import datetime, timedelta
from triggerInterface import TriggerInterface
from collections import namedtuple
import random
import logging


class TimeTrigger(TriggerInterface):
    supportedClass = 'TimeTrigger'
    Runable = namedtuple('TimeTrigger', TriggerInterface.Runable._fields + ('time', 'variance', 'mustStayActive', 'trigger'))

    def __init__(self, trigger, **kwargs):
        super(TimeTrigger, self).__init__(trigger, **kwargs)
        self._lastState = None
        self._lastActive = None
        self._lastChange = None
        self._ti = None

    @property
    def _triggerInt(self):
        # Can not be configured in the constructor or it will break the caching and cause infinite recursion if self-referenced
        if not self._ti:
            if self._trigger.trigger == 'self':
                return self
            elif self._trigger.trigger:
                self._ti = TriggerInterface.getTriggerInterface(self._trigger.trigger)
        return self._ti

    @staticmethod
    def getRunable(trigger):
        if trigger.type == TimeTrigger.supportedClass:
            if trigger.trigger == trigger:
                t = 'self'
            else:
                t = TimeTrigger.getRunable(trigger.trigger)
            return TimeTrigger.Runable(trigger.name, trigger.id, trigger.type, trigger.time, trigger.variance, trigger.mustStayActive, t)
        else:
            logger = logging.getLogger(TimeTrigger.__name__)
            logger.error("Trigger: %s has an unknown trigger type: %s" % (trigger.name, trigger.type))
            return None

    def getActive(self):
        # triggers can be self-referencing
        if self._triggerInt == self:
            active = False
        elif self._triggerInt:
            active = self._triggerInt.getActive()
        else:
            #TODO: Error handling
            return False

        if active != self._lastState:
            self._lastChange = datetime.now()
            self._lastState = active
            self._time = timedelta(seconds=self._trigger.time + random.randint(-1 * self._trigger.variance, self._trigger.variance))

        if active:
            try:
                self._lastActive = self._lastChange
            except:
                pass

        if self._trigger.mustStayActive:
            active = active and datetime.now() - self._lastActive >= self._time
        else:
            active = not active and datetime.now() - self._lastChange >= self._time

        if self._triggerInt == self:
            self._lastState = active
        return active

