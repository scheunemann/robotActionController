from datetime import datetime, timedelta
from triggerInterface import TriggerInterface
import random


class TimeTrigger(TriggerInterface):

    def __init__(self, trigger, **kwargs):
        super(TimeTrigger, self).__init__(trigger, **kwargs)
        self._lastState = None
        self._lastActive = None
        self._lastChange = None
        self._variance = self._trigger.variance
        self._ti = None

    @property
    def _triggerInt(self):
        # Can not be configured in the constructor or it will break the caching and cause infinite recursion if self-referenced
        if not self._ti:
            self._ti = TriggerInterface.getTriggerInterface(self._trigger.trigger) if self._trigger.trigger else None
        return self._ti

    def getActive(self):
        # triggers can be self-referencing
        if self._triggerInt == self:
            active = False
        else:
            active = self._triggerInt.getActive()

        if active != self._lastState:
            self._lastChange = datetime.now()
            self._lastState = active
            self._time = timedelta(seconds=self._trigger.time + random.randint(-1 * self._variance, self._variance))

        if active:
            self._lastActive = self._lastChange

        if self._trigger.mustStayActive:
            active = active and datetime.now() - self._lastActive >= self._time
        else:
            active = not active and datetime.now() - self._lastChange >= self._time

        if self._triggerInt == self:
            self._lastState = active
        return active

