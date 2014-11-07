import logging
from evdev import InputDevice, ecodes
from select import select
from sets import Set
from collections import namedtuple
from robotActionController.Processor.event import Event
from gevent import spawn, sleep

__all__ = ['KeyEvents']


class KeyEvents(object):

    KeyEventArg = namedtuple('KeyEventArg', ['alt', 'ctrl', 'shift', 'keyCode', 'keyValue', 'keyRaw', 'modifiers'])
    keyUpEvent = Event('Key up event')
    keyDownEvent = Event('Key down event')

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
            'LEFTALT': 'lalt',
            'RIGHTALT': 'ralt',
            'LEFTSHIFT': 'lshift',
            'RIGHTSHIFT': 'rshift',
            'LEFTCTRL': 'lctrl',
            'RIGHTCTRL': 'rctrl',
          }

    def __init__(self, inputName='keyPad', exclusive=False):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._thread = spawn(self._bindKeys, inputName, exclusive)
        self._altKeys = ['KEY_LEFTALT', 'KEY_RIGHTALT']
        self._shiftKeys = ['KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT']
        self._ctrlKeys = ['KEY_LEFTCTRL', 'KEY_RIGHTCTRL']


    def __processEvent(self, modifiers, event, key):
        alt = len(modifiers['alt']) > 0
        shift = len(modifiers['shift']) > 0
        ctrl = len(modifiers['ctrl']) > 0
        mods = []
        mods.extend(modifiers['alt'])
        mods.extend(modifiers['shift'])
        mods.extend(modifiers['ctrl'])
        mods = [KeyEvents.keyMap.get(k[4:], k[4:].lower()) for k in mods]
        keyName = KeyEvents.keyMap.get(key[4:], key[4:])
        k = KeyEvents.KeyEventArg(alt, ctrl, shift, event.code, keyName, key[4:], mods)
        return k


    def _bindKeys(self, inputName, grab):
        try:
            self._input = InputDevice('/dev/input/' + inputName)
            if grab:
                self._input.grab()
            select([self._input], [], [])
            modifiers = dict([('alt', Set()), ('ctrl', Set()), ('shift', Set())])

            try:
                for event in self._input.read_loop():
                    if event.type == ecodes.EV_KEY:
                        if event.value == 2:  # keyHold
                            continue

                        key = ecodes.keys[event.code]
                        if event.value == 1:  # keyDown
                            if key in self._altKeys:
                                modifiers['alt'].add(key)
                            elif key in self._ctrlKeys:
                                modifiers['ctrl'].add(key)
                            elif key in self._shiftKeys:
                                modifiers['shift'].add(key)
                            else:
                                k = self.__processEvent(modifiers, event, key)
                                try:
                                    self.keyDownEvent(k)
                                except:
                                    pass
                        elif event.value == 0:  # keyUp
                            if key in self._altKeys:
                                modifiers['alt'].discard(key)
                            elif key in self._ctrlKeys:
                                modifiers['ctrl'].discard(key)
                            elif key in self._shiftKeys:
                                modifiers['shift'].discard(key)
                            else:
                                k = self.__processEvent(modifiers, event, key)
                                try:
                                    self.keyUpEvent(k)
                                except:
                                    pass
                    sleep(0)
            except KeyboardInterrupt:
                pass
            finally:
                if grab:
                    self._input.ungrab()
        except Exception:
            self._logger.error("Unable to open input: %s" % inputName, exc_info=True)


def printEvt(sender, evt):
    print evt

if __name__ == '__main__':
    device = 'keyPad'
    k = KeyEvents(device, True)
    k.keyDownEvent += printEvt
    k.keyUpEvent += printEvt
    k._thread.join()
