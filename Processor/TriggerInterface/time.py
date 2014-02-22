from datetime import datetime
from triggerInterface import TriggerInterface
import random


class TimeTrigger(TriggerInterface):

    def __init(self, trigger):
        super(TimeTrigger, self).__init__(trigger)
        self._lastState = None
        self._lastActive = None
        self._lastChange = None
        self._variance = self._trigger.variance
        if trigger.triggers:
            self._triggerInts = [TriggerInterface.getTriggerInterface(t) for t in trigger.triggers]

    def getActive(self):
        # Be sure to exclude 'self' as triggers can be self-referencing
        interfaces = [ti for ti in self._triggerInts if ti != self]
        if interfaces:
            if self._trigger.requireAll:
                active = all([ti.getActive() for ti in interfaces])
            else:
                active = any([ti.getActive() for ti in interfaces])

        if active != self._lastState:
            self._lastChange = datetime.now()
            self._time = self._trigger.time + random.randint(-1 * self._variance, self._variance)

        if active:
            self._lastActive = self._lastChange

        if self._trigger.mustStayActive:
            return active and datetime.now() - self._lastActive >= self._time
        else:
            return not active and datetime.now() - self._lastChange >= self._time
