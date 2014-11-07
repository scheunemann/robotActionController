from sets import Set
from collections import namedtuple
from robotActionController.Processor.event import Event
import pyHook
from pythoncom import PumpMessages, PumpWaitingMessages
from gevent import spawn, sleep
import logging

__all__ = ['KeyEvents']


class KeyEvents(object):

    KeyEventArg = namedtuple('KeyEventArg', ['alt', 'ctrl', 'shift', 'keyCode', 'keyValue', 'keyRaw', 'modifiers'])
    keyUpEvent = Event('Key up event')
    keyDownEvent = Event('Key down event')

    keyMap = {\
            'Oem_5': '\\',  # This is due to US vs UK kb layout (see above)
            'Oem_3': '\'',
            'Oem_7': '#',  # This is due to US vs UK kb layout (see above)
            'Oem_Comma': ',',
            'Delete': 'del',
            'Oem_Period': '.',
            'Oem_Plus': '=',
            'Escape': 'escape',
            'Oem_8': '`',
            'Insert': 'ins',
            'Numpad0': '0',
            'Numpad1': '1',
            'Numpad2': '2',
            'Numpad3': '3',
            'Numpad4': '4',
            'Numpad5': '5',
            'Numpad6': '6',
            'Numpad7': '7',
            'Numpad8': '8',
            'Numpad9': '9',
            'Multiply': '*',
            'Decimal': '.',
            'Return': 'enter',
            'Subtract': '-',
            'Add': '+',
            'Divide': '/',
            'Oem_4': '[',
            'Oem_Minus': '-',
            'Oem_6': ']',
            'Oem_1': ';',
            'Oem_2': '/',
            'Prior': 'pageup',
            'Next': 'pagedown',
            'Back': 'backspace',
            'Lmenu': 'lalt',
            'Rmenu': 'ralt',
            'Lshift': 'lshift',
            'Rshift': 'rshift',
            'Lcontrol': 'lctrl',
            'Rcontrol': 'rctrl',
          }

    def __init__(self, inputName=None, exclusive=False):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._input = pyHook.HookManager()
        self._input.KeyDown = lambda x: self._keyDown(x)
        self._input.KeyUp = lambda x: self._keyUp(x)
        self._input.HookKeyboard()
        self._eat = exclusive
        self._altKeys = Set(['Lmenu', 'Rmenu'])
        self._shiftKeys = Set(['Lshift', 'Rshift'])
        self._ctrlKeys = Set(['Lcontrol', 'Rcontrol'])
        self._downKeys = Set()
        self._thread = spawn(self._pumpMsgs)

    def _pumpMsgs(self):
        while True:
            PumpWaitingMessages()
            sleep(0)

    def _keyDown(self, event):
        #attribs = ['Alt', 'Ascii', 'Extended', 'Injected', 'Key', 'KeyID', 'Message', 'MessageName', 'ScanCode', 'Time', 'Transition', 'Window', 'WindowName']
        #meths = ['GetKey', 'GetMessageName', 'IsAlt', 'IsExtended', 'IsInjected', 'IsTransition', ]
        if event.Key not in self._downKeys:
            self._downKeys.add(event.Key)
            k = self.__processEvent(event)
            try:
                self.keyDownEvent(k)
                self._logger.log(1, "KeyDown %s" % (k, ))
            except:
                pass
        return not self._eat


    def _keyUp(self, event):
        if event.Key in self._downKeys:
            self._downKeys.discard(event.Key)
            k = self.__processEvent(event)
            try:
                self.keyUpEvent(k)
                self._logger.log(1, "KeyUp %s" % (k, ))
            except:
                pass
        return not self._eat

    def __processEvent(self, event):
        alt = self._downKeys.intersection(self._altKeys)
        ctrl = self._downKeys.intersection(self._ctrlKeys)
        shift = self._downKeys.intersection(self._shiftKeys)
        mods = []
        mods.extend(alt)
        mods.extend(ctrl)
        mods.extend(shift)
        mods = [KeyEvents.keyMap.get(k, k) for k in mods]
        if not event.Key:
            print event.ScanCode

        keyName = KeyEvents.keyMap.get(event.Key, event.Key.lower())
        k = KeyEvents.KeyEventArg(bool(alt), bool(ctrl), bool(shift), event.ScanCode, keyName, event.Key, mods)
        return k


if __name__ == '__main__':

    device = 'keyPad'
    k = KeyEvents(device, False)
    def p(msg): print msg
    k.keyDownEvent += lambda s, e: p("KeyDown: %s" % (e, ))
    #k.keyUpEvent += lambda s, e: p("KeyUp: %s" % (e, ))
    k._thread.join()
