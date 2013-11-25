#!/usr/bin/env python
#
# dynamixel.py
# Mac Mason <mac@cs.duke.edu>
#
# Pythonic access to a Robotis AX-12 servo. Requires pySerial, but is
# otherwise pure Python, and should Just Work.
#
# There are two classes defined here; Response, which you probably don't care
# about, and ServoController, which you almost certainly do. A ServoController
# controls as many servos as you have plugged into a single port; each
# function takes a servo id_ as its first argument, and then the actual meat of
# the instruction after that. See the individual function documentation for
# details. This doesn't implement every single option provided by the AX-12+,
# just the ones I need. However, using the existing functions as templates for
# new functions is as easy as copy-and-paste. The sole exception to this is
# that I haven't implemented broadcast packets; that would be trickier. I make
# many references to the AX-12 user manual, which you can easily find by
# googling.
#
# The values in the ERRORS dictionary describe all the things that might go
# wrong.
#
# For a (very!) simple example of use, see the end of dynamixel.py.
#
# This code is made available under a Creative Commons
# Attribution-Noncommercial-Share-Alike 3.0 license. See
# <http://creativecommons.org/licenses/by-nc-sa/3.0> for details. If you'd
# like some other license, send me an e-mail. If you're doing something cool
# with this code, send me an e-mail, too: I'd like to see it.


import sys
import serial
import time
from threading import RLock

__all__ = ['ServoController', ]

"""
# POS_SCALE = 0.352
# POS_OFFSET = 0
# SPEED_SCALE = 0.36
"""

# The types of packets.
PING = [0x01]
READ_DATA = [0x02]
WRITE_DATA = [0x03]
REG_WRITE = [0x04]
ACTION = [0x05]
RESET = [0x06]
SYNC_WRITE = [0x83]

# The various errors that might take place.
ERRORS = {
            64: "Instruction",
            32: "Overload",
            16: "Checksum",
            8: "Range",
            4: "Overheating",
            2: "AngleLimit",
            1: "InputVoltage"
         }


def _Checksum(s):
    """Calculate the Dynamixel checksum (~(id_ + length + ...)) & 0xFF."""
    return (~sum(s)) & 0xFF


def _VerifyID(id_):
    """
    Just make sure the id_ is valid.
    """
    if not (0 <= id_ <= 0xFD):
        raise ValueError("id_ %d isn't legal!" % id_)


def _EnWire(v):
    """
    Convert an int to the on-wire (little-endian) format. Actually returns the
    list [lsbyte, msbyte]. Of course, this is only useful for the 16-bit
    quantities we need to deal with.
    """
    if not 0 <= v <= 1023:
        raise ValueError("EnWiring illegal value: %d" % v)
    return [v & 255, v >> 8]


def _DeWire(v):
    """
    Invert EnWire. v should be the list [lsbyte, msbyte].
    """
    return (v[1] << 8) + v[0]


class Response:
    """
    A response packet. Takes care of parsing the response, and figuring what (if
    any) errors have occurred. These will appear in the errors field, which is a
    list of strings, each of which is an element of ERRORS.values().
    """
    def __init__(self, data):
        """
        Data should be the result of a complete read from the serial port, as a
        list of ints. See ServoController.Interact().
        """
        if len(data) == 0 or data[0] != 0xFF or data[1] != 0xFF:
            raise ValueError("Bad Header! ('%s')" % str(data))
        if _Checksum(data[2:-1]) != data[-1]:
            raise ValueError("Checksum %s should be %s" % (_Checksum(data[2:-1]), data[-1]))
        self.data = data
        self.id_, self.length = data[2:4]
        self.errors = []
        for k in ERRORS.keys():
            if data[4] & k != 0:
                self.errors.append(ERRORS[k])
        # Lastly, the data we actually asked for, if any.
        self.parameters = self.data[5:-1]

    def __str__(self):
        return " ".join(map(hex, self.data))

    def Verify(self):
        """
        Ensure that nothing went wrong.
        """
        if len(self.errors) != 0:
            raise ValueError("ERRORS: %s" % " ".join(self.errors))
        return self  # Syntactic sugar; lets us do return foo.Verify().


class ServoController:
    """
    Interface to a servo. Most of the real work happens in Interact(), which
    does a complete round of send-and-recv. The rest of the functions do what it
    sounds like they do. Note that this represents an entire _collection_ of
    servos, not just a single servo: therefore, each function takes a servo id_
    as its first argument, to specify the servo that should get the command.
    """
    def __init__(self, portstring, portspeed):
        """
        Provide the name of the serial port to which the servos are connected.
        """
        self.portstring = portstring
        self.portLock = RLock()
        self.port = serial.Serial(port=self.portstring, baudrate=portspeed, timeout=5)  # Picked from a hat.

    def Close(self):
        """Close the serial port."""
        self.port.close()

    def __del__(self):
        """
        All this needs to do is shut down, which you can also do by hand using
        Close().
        """
        self.Close()

    def Interact(self, id_, packet):
        """
        Given an (assembled) payload, add the various extra bits, and transmit to
        servo at id_. Returns the status packet as a Response. id_ must be in the
        range [0, 0xFD].

        Note that the payload should be a list of integers, suitable for passing
        to chr(). See the user manual, page 10, for what's going on here.

        This is the low-level communication function; you probably want one of the
        other functions that does specific things.
        """
        _VerifyID(id_)
        P = [id_, len(packet) + 1] + packet
        with self.portLock:
            self.port.write("".join(map(chr, [0xFF, 0xFF] + P + [_Checksum(P)])))
            self.port.flushOutput()
            time.sleep(0.05)

            # Handle the read.
            res = []
            while self.port.inWaiting() > 0:
                res.append(self.port.read())
        return Response(map(ord, res)).Verify()

    # From here on out, you're looking at functions that really do something to
    # the servo itself. You should look at the user manual for details on what
    # all of these mean, although most are self-explanatory.
    def Reset(self, id_):
        """
        Perform a reset on the servo. Note that this will reset the id_ to 1, which
        could be messy if you have many servos plugged in.
        """
        _VerifyID(id_)
        self.Interact(id_, RESET).Verify()

    def GetPosition(self, id_):
        """
        Return the current position of the servo. See the user manual, page 16,
        for what the return value means.
        """
        _VerifyID(id_)
        packet = READ_DATA + [0x24] + [2]
        res = self.Interact(id_, packet).Verify()
        if len(res.parameters) != 2:
            raise ValueError("GetPosition didn't get two parameters!")
        return _DeWire(res.parameters)

    def GetPositionDegrees(self, id_):
        """
        If you'd rather work in degrees, use this one. Again, see the user manual,
        page 16, for details.
        """
        return self.GetPosition(id_) * (300.0 / 1023.0)

    def SetPosition(self, id_, position):
        """
        Set servo id_ to be at position position. See the user manual, page 16, for
        how this works. This just sends the set position packet; the servo won't
        necessarily go where you told it. You can use GetPosition to figure out
        where it actually went.
        """
        _VerifyID(id_)
        if not (0 <= position <= 1023):
            raise ValueError("Invalid position! (%s)", position)
        packet = WRITE_DATA + [0x1e] + _EnWire(position)
        self.Interact(id_, packet).Verify()

    def SetPositionDegrees(self, id_, deg):
        """
        Set the position in degrees, according to the diagram in the manual on
        page 16.
        """
        if not 0 <= deg <= 300:
            raise ValueError("%d is not a valid angle!" % deg)
        self.SetPosition(id_, int(1023.0 / 300 * deg))

    def SetComplianceMargin(self, id_, margin):
        """
        Set both the CW and CCW compliance margins.
        """
        _VerifyID(id_)
        if not 0 <= margin < 256:
            raise ValueError("%d is not a valid margin!" % margin)
        packetcw = WRITE_DATA + [0x1a] + [int(margin)]  # CW
        packetccw = WRITE_DATA + [0x1b] + [int(margin)]  # CCW
        self.Interact(id_, packetcw).Verify()
        self.Interact(id_, packetccw).Verify()

    def GetComplianceMargin(self, id_):
        """
        Return the compliance margins as (CW, CCW).
        """
        _VerifyID(id_)
        packetcw = READ_DATA + [0x1a] + [1]
        packetccw = READ_DATA + [0x1b] + [1]
        Q = self.Interact(id_, packetcw).Verify()
        if len(Q.parameters) != 1:
            raise ValueError("CW Compliance Margin parameter count problem!")
        temp = Q.parameters[0]
        Q = self.Interact(id_, packetccw).Verify()
        if len(Q.parameters) != 1:
            raise ValueError("CCW Compliance Margin parameter count problem!")
        return (temp, Q.parameters[0])

    def SetCWAngleLimit(self, id_, limit):
        """
        Set the clockwise (smaller) angle limit, in servo units.
        """
        _VerifyID(id_)
        if not 0 <= limit <= 1023:
            raise ValueError("%d is not a valid CW angle limit!" % limit)
        packet = WRITE_DATA + [0x06] + _EnWire(limit)
        self.Interact(id_, packet).Verify()

    def GetCWAngleLimit(self, id_):
        _VerifyID(id_)
        packet = READ_DATA + [0x06] + [2]
        Q = self.Interact(id_, packet).Verify()
        if len(Q.parameters) != 2:
            raise ValueError("GetCWAngleLimit has the wrong return shape!")
        return _DeWire(Q.parameters)

    def SetCCWAngleLimit(self, id_, limit):
        """
        Set the counterclockwise (larger) angle limit, in servo units.
        """
        _VerifyID(id_)
        if not 0 <= limit <= 1023:
            raise ValueError("%d is not a valid CCW angle limit!" % limit)
        packet = WRITE_DATA + [0x08] + _EnWire(limit)
        self.Interact(id_, packet).Verify()

    def GetCCWAngleLimit(self, id_):
        _VerifyID(id_)
        packet = READ_DATA + [0x08] + [2]
        Q = self.Interact(id_, packet).Verify()
        if len(Q.parameters) != 2:
            raise ValueError("GetCCWAngleLimit has the wrong return shape!")
        return _DeWire(Q.parameters)

    def SetID(self, id_, nid):
        """
        Change the id_ of a servo. Note that this is persistent; you may also be
        interested in Reset().
        """
        _VerifyID(id_)
        if not 0 <= nid <= 253:
            raise ValueError("%id_ is not a valid servo id_!" % nid)
        packet = WRITE_DATA + [0x03] + [nid]
        self.Interact(id_, packet).Verify()

    def GetMovingSpeed(self, id_):
        """
        Get the moving speed. 0 means "unlimited".
        """
        _VerifyID(id_)
        packet = READ_DATA + [0x20] + [2]
        Q = self.Interact(id_, packet).Verify()
        if len(Q.parameters) != 2:
            raise ValueError("GetMovingSpeed has the wrong return shape!")
        return _DeWire(Q.parameters)

    def SetTorqueEnable(self, id_, value):
        """
        Set the moving speed. 0 means "unlimited", so the servo will move as fast
        as it can.
        """
        _VerifyID(id_)
        if not 0 <= value <= 1:
            raise ValueError("%d is not a torque setting!" % value)
        packet = WRITE_DATA + [0x18] + _EnWire(value)
        self.Interact(id_, packet).Verify()

    def SetMovingSpeed(self, id_, speed):
        """
        Set the moving speed. 0 means "unlimited", so the servo will move as fast
        as it can.
        """
        _VerifyID(id_)
        if not 0 <= speed <= 1023:
            raise ValueError("%d is not a valid moving speed!" % speed)
        packet = WRITE_DATA + [0x20] + _EnWire(speed)
        self.Interact(id_, packet).Verify()

    def Moving(self, id_):
        """
        Return True if the servo is currently moving, False otherwise.
        """
        _VerifyID(id_)
        packet = READ_DATA + [0x2e] + [1]
        Q = self.Interact(id_, packet).Verify()
        return Q.parameters[0] == 1

    def WaitUntilStopped(self, id_):
        """
        Spinlock until the servo has stopped moving.
        """
        while self.Moving(id_):
            time.sleep(0.001)

# Handy for interactive testing.
if __name__ == "__main__":
    if len(sys.argv) != 1:  # Specifying a port for interactive use
        ps = sys.argv[1]
    else:
        ps = "/dev/ttyUSB1"
    X = ServoController(ps)
    X.SetPosition(1, 512)  # Set servo id 1 to position 512 (straight up)
