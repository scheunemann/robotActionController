from triggerInterface import TriggerInterface
from collections import namedtuple
from Processor.hotKeys import KeyEvents
import logging


class ButtonTrigger(TriggerInterface):
    supportedClass = 'ButtonTrigger'
    Runable = namedtuple('ButtonTrigger', TriggerInterface.Runable._fields + ('keybindings', ))
    keyEvents = None

    # Match with the javscript side of things, should cover most common keys
    # Unfortunately evdev doesn't take the KB layout into account, hopefully won't be an issue with our usage
    keyMap = {
            '102ND': '\\',  # This is due to US vs UK kb layout (see above)
            'APOSTROPHE': '\'',
            'BACKSLASH': '#',  # This is due to US vs UK kb layout (see above)
            'COMMA': ',',
            'DELETE': 'del',
            'DOT': '.',
            'EQUAL': '=',
            'ESC': 'escape',
            'GRAVE': '`',
            'INSERT': 'ins',
            'KP0': '0',
            'KP1': '1',
            'KP2': '2',
            'KP3': '3',
            'KP4': '4',
            'KP5': '5',
            'KP6': '6',
            'KP7': '7',
            'KP8': '8',
            'KP9': '9',
            'KPASTERISK': '*',
            'KPDOT': '.',
            'KPENTER': 'enter',
            'KPMINUS': '-',
            'KPPLUS': '+',
            'KPSLASH': '/',
            'LEFTBRACE': '[',
            'MINUS': '-',
            'RIGHTBRACE': ']',
            'SEMICOLON': ';',
            'SLASH': '/',
          }

    def __init__(self, trigger, **kwargs):
        super(ButtonTrigger, self).__init__(trigger, **kwargs)
        if ButtonTrigger.keyEvents == None:
            ButtonTrigger.keyEvents = KeyEvents()

        if trigger.keybindings:
            ButtonTrigger.keyEvents.keyUpEvent += self.handleKeyPress
            self._keybindings = trigger.keybindings

        self._active = False

    def __del__(self):
        try:
            ButtonTrigger.keyEvents.keyUpEvent -= self.handleKeyPress
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
        return self._active

    def _formatKeyEvent(self, keyEventArg):
        modifiers = ""
        if keyEventArg.alt:
            modifiers += "alt+"

        if keyEventArg.ctrl:
            modifiers += "ctrl+"

        if keyEventArg.shift:
            modifiers += "shift+"

        disp = keyEventArg.keyValue
        if disp in ButtonTrigger.keyMap:
            disp = ButtonTrigger.keyMap[disp]

        return (modifiers + disp).upper().strip('+')

    def handleKeyPress(self, sender, keyEventArg):
        self._active = self._formatKeyEvent(keyEventArg) in self._keybindings
