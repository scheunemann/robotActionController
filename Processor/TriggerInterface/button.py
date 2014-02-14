from triggerInterface import TriggerInterface


class ButtonTrigger(TriggerInterface):

    def __init__(self, trigger):
        super(ButtonTrigger, self).__init__(trigger)
        keybindings = [t.keyString for t in trigger.hotKeys]
        if keybindings:
            self._bindKeys(keybindings)

    def getActive(self):
        return False

    def _bindKeys(self, keybindings):
        pass
