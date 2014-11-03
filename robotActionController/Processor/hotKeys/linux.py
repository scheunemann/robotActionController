import logging
from evdev import InputDevice, ecodes
from select import select
from sets import Set
from collections import namedtuple
from robotActionController.Processor.event import Event
from threading import Thread

__all__ = ['KeyEvents']


class KeyEvents(object):

    KeyEventArg = namedtuple('KeyEventArg', ['alt', 'ctrl', 'shift', 'keyCode', 'keyValue', 'modifiers'])
    keyUpEvent = Event('Key up event')
    keyDownEvent = Event('Key down event')

    def __init__(self, inputName='keyPad', exclusive=False):
        """Should probably set up udev rules for the keypad so that it's mapped to a named input"""
        # SUBSYSTEM=="input", KERNEL=="event*", ATTRS{idVendor}=="????", ATTRS{idProduct}=="????", SYMLINK+="input/keyPad", MODE="0666"
        # For the logitech keypads:
        # SUBSYSTEM=="input", KERNEL=="event*", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="c52b", SYMLINK+="input/keyPad", GROUP="input", MODE="0660"
        # use 'udevadm info --name=/dev/input/by-id/?? --attribute-walk' to find device attrs
        # SUBSYSTEMS=="usb", ATTRS{idVendor}=="1ffb", ATTRS{idProduct}=="008b", ATTRS{iad_bFirstInterface}=="00", SYMLINK+="servos", GROUP="input", MODE="0660"
        # SUBSYSTEMS=="usb", ATTRS{idVendor}=="1ffb", ATTRS{idProduct}=="008b", ATTRS{iad_bFirstInterface}=="02", SYMLINK+="sensors", GROUP="input", MODE="0660"
        self._logger = logging.getLogger(self.__class__.__name__)
        self._thread = Thread(target=self._bindKeys, args=(inputName, exclusive))
        self._thread.setDaemon(True)
        self._thread.start()
        self._altKeys = ['KEY_LEFTALT', 'KEY_RIGHTALT']
        self._shiftKeys = ['KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT']
        self._ctrlKeys = ['KEY_LEFTCTRL', 'KEY_RIGHTCTRL']
        self._modifiers = []
        self._modifiers.extend(self._altKeys)
        self._modifiers.extend(self._shiftKeys)
        self._modifiers.extend(self._ctrlKeys)

    def _bindKeys(self, inputName, grab):
        try:
            self._input = InputDevice('/dev/input/' + inputName)
            if grab:
                self._input.grab()
            select([self._input], [], [])
            ['event', 'key_down', 'key_hold', 'key_up', 'keycode', 'scancode']
            modifiers = dict([('alt', Set()), ('ctrl', Set()), ('shift', Set())])

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
                            alt = len(modifiers['alt']) > 0
                            shift = len(modifiers['shift']) > 0
                            ctrl = len(modifiers['ctrl']) > 0
                            mods = []
                            mods.extend(modifiers['alt'])
                            mods.extend(modifiers['shift'])
                            mods.extend(modifiers['ctrl'])
                            mods = [k[4:] for k in mods]
                            k = KeyEvents.KeyEventArg(alt, ctrl, shift, event.code, key[4:], mods)
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
                            alt = len(modifiers['alt']) > 0
                            shift = len(modifiers['shift']) > 0
                            ctrl = len(modifiers['ctrl']) > 0
                            mods = []
                            mods.extend(modifiers['alt'])
                            mods.extend(modifiers['shift'])
                            mods.extend(modifiers['ctrl'])
                            mods = [k[4:] for k in mods]
                            k = KeyEvents.KeyEventArg(alt, ctrl, shift, event.code, key[4:], mods)
                            try:
                                self.keyUpEvent(k)
                            except:
                                pass
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
