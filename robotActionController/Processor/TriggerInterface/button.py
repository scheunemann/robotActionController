from triggerInterface import TriggerInterface
from collections import namedtuple
from robotActionController.Processor.hotKeys import KeyEvents
import logging
from gevent.lock import RLock
from gevent import spawn, sleep


class ButtonTrigger(TriggerInterface):
    supportedClass = 'ButtonTrigger'
    Runable = namedtuple('ButtonTrigger', TriggerInterface.Runable._fields + ('keybindings', ))
    keyEvents = None
    __threadLock = RLock()

    def __init__(self, trigger, **kwargs):
        super(ButtonTrigger, self).__init__(trigger, **kwargs)
        with ButtonTrigger.__threadLock:
            if ButtonTrigger.keyEvents == None:
                ButtonTrigger.keyEvents = KeyEvents()

        if trigger.keybindings:
            ButtonTrigger.keyEvents.keyDownEvent += self.handleKeyPress
            ButtonTrigger.keyEvents.keyUpEvent += self.handleKeyRelease
            self._keybindings = trigger.keybindings

        self._active = False
        self._disableActive = False

    def __del__(self):
        try:
            ButtonTrigger.keyEvents.keyDownEvent -= self.handleKeyPress
            ButtonTrigger.keyEvents.keyUpEvent -= self.handleKeyRelease
        except:
            pass

    @staticmethod
    def getRunable(trigger):
        if trigger.type == ButtonTrigger.supportedClass:
            keybindings = [t.keyString.upper() for t in trigger.hotKeys]
            return ButtonTrigger.Runable(trigger.name, trigger.id, trigger.type, keybindings)
        else:
            logger = logging.getLogger(ButtonTrigger.__name__)
            logger.error("Trigger: %s has an unknown trigger type: %s" % (trigger.name, trigger.type))
            return None

    def getActive(self):
        active = self._active
        if self._disableActive:
            self._active = False
        return active

    def _formatKeyEvent(self, keyEventArg):
        modifiers = ""
        if keyEventArg.alt:
            modifiers += "alt+"

        if keyEventArg.ctrl:
            modifiers += "ctrl+"

        if keyEventArg.shift:
            modifiers += "shift+"

        if modifiers and keyEventArg.keyValue:
            return (modifiers + keyEventArg.keyValue).upper()
        elif modifiers:
            return modifiers.rstrip('+').upper()
        elif keyEventArg.keyValue:
            return keyEventArg.keyValue.upper()
        else:
            return None

    def delayDisable(self, delayTime):
        sleep(delayTime)
        if self._disableActive:
            self._active = False

    def handleKeyRelease(self, sender, keyEventArg):
        released = self._formatKeyEvent(keyEventArg) in self._keybindings
        if self._active and released:
            self._disableActive = True
            # Prevent missing brief presses
            spawn(self.delayDisable, 0.1)
        if released:
            self._logger.debug("KeyEvent: %s, active: %s, keybindings: %s" % (keyEventArg, self._active, self._keybindings))

    def handleKeyPress(self, sender, keyEventArg):
        pressed = self._formatKeyEvent(keyEventArg) in self._keybindings
        if not self._active and pressed:
            self._disableActive = False
            self._active = True
        if self._active:
            self._logger.debug("KeyEvent: %s, active: %s, keybindings: %s" % (keyEventArg, self._active, self._keybindings))
