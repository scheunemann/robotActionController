"""
* HerkuleX
* A Python Processing library for Dongbu HerkuleX Servo adapted from:
* https://github.com/dongburobot/HerkuleXProcessing/
*
* This library is free software you can redistribute it and/or
* modify it under the terms of the GNU Lesser General Public
* License as published by the Free Software Foundation either
:* version 2.1 of the License, or (at your option) any later version.
*
* This library is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
* Lesser General Public License for more details.
*
* You should have received a copy of the GNU Lesser General
* Public License along with this library if not, write to the
* Free Software Foundation, Inc., 59 Temple Place, Suite 330,
* Boston, MA  02111-1307  USA
*
* @author: Nathan Burke (natbur@natbur.com)
* @modified    2013.10.10
* @version     0.1
"""

import sys
import time
import logging
from threading import RLock
from robotActionController import connections

__all__ = ['HerkuleX', ]


class HerkuleX(object):

    """
    POS_SCALE = 0.325
    POS_OFFSET = 512
    SPEED_SCALE = (0.68 * steps) #nominal steps per second
    """

    BASIC_PKT_SIZE = 7
    WAIT_TIME_BY_ACK = 30
    MAX_PLAY_TIME = 2856

    # SERVO HERKULEX COMMAND - See Manual p40
    HEEPWRITE = 0x01  # Rom write
    HEEPREAD = 0x02  # Rom read
    HRAMWRITE = 0x03  # Ram write
    HRAMREAD = 0x04  # Ram read
    HIJOG = 0x05  # Write n servo with different timing
    HSJOG = 0x06  # Write n servo with same time
    HSTAT = 0x07  # Read error
    HROLLBACK = 0x08  # Back to factory value
    HREBOOT = 0x09  # Reboot

    # HERKULEX Broadcast Servo ID
    BROADCAST_ID = 0xFE

    # HERKULEX LED - See Manual p29
    LED_RED = 0x10
    LED_GREEN = 0x04
    LED_BLUE = 0x08

    # HERKULEX STATUS ERROR - See Manual p39
    H_STATUS_OK = 0x00
    H_ERROR_INPUT_VOLTAGE = 0x01
    H_ERROR_POS_LIMIT = 0x02
    H_ERROR_TEMPERATURE_LIMIT = 0x04
    H_ERROR_INVALID_PKT = 0x08
    H_ERROR_OVERLOAD = 0x10
    H_ERROR_DRIVER_FAULT = 0x20
    H_ERROR_EEPREG_DISTORT = 0x40

    H_DETAIL_MOVING = 0x01
    H_DETAIL_INPOSITION = 0x02
    H_PKTERR_CHECKSUM = 0x04
    H_PKTERR_UNKNOWN_CMD = 0x08
    H_PKTERR_EXCEED_REG_RANGE = 0x10
    H_PKTERR_GARBAGE = 0x20
    H_DETAIL_MOTORON = 0x04

    T_ADC = {
        0: -79.47,
        1: -71.78,
        2: -63.2,
        3: -57.81,
        4: -53.8,
        5: -50.58,
        6: -47.86,
        7: -45.49,
        8: -43.4,
        9: -41.51,
        10: -39.79,
        11: -38.2,
        12: -36.73,
        13: -35.35,
        14: -34.06,
        15: -32.83,
        16: -31.67,
        17: -30.57,
        18: -29.51,
        19: -28.5,
        20: -27.53,
        21: -26.59,
        22: -25.69,
        23: -24.82,
        24: -23.97,
        25: -23.15,
        26: -22.36,
        27: -21.59,
        28: -20.83,
        29: -20.1,
        30: -19.38,
        31: -18.68,
        32: -18,
        33: -17.33,
        34: -16.67,
        35: -16.03,
        36: -15.39,
        37: -14.77,
        38: -14.17,
        39: -13.57,
        40: -12.98,
        41: -12.4,
        42: -11.83,
        43: -11.26,
        44: -10.71,
        45: -10.16,
        46: -9.62,
        47: -9.09,
        48: -8.56,
        49: -8.04,
        50: -7.53,
        51: -7.02,
        52: -6.52,
        53: -6.02,
        54: -5.53,
        55: -5.04,
        56: -4.56,
        57: -4.08,
        58: -3.61,
        59: -3.14,
        60: -2.67,
        61: -2.21,
        62: -1.75,
        63: -1.29,
        64: -0.84,
        65: -0.39,
        66: 0.05,
        67: 0.49,
        68: 0.93,
        69: 1.37,
        70: 1.81,
        71: 2.24,
        72: 2.67,
        73: 3.1,
        74: 3.52,
        75: 3.94,
        76: 4.37,
        77: 4.78,
        78: 5.2,
        79: 5.62,
        80: 6.03,
        81: 6.44,
        82: 6.86,
        83: 7.27,
        84: 7.67,
        85: 8.08,
        86: 8.49,
        87: 8.89,
        88: 9.29,
        89: 9.7,
        90: 10.1,
        91: 10.5,
        92: 10.9,
        93: 11.3,
        94: 11.7,
        95: 12.09,
        96: 12.49,
        97: 12.89,
        98: 13.28,
        99: 13.68,
        100: 14.07,
        101: 14.47,
        102: 14.86,
        103: 15.26,
        104: 15.65,
        105: 16.05,
        106: 16.44,
        107: 16.84,
        108: 17.23,
        109: 17.62,
        110: 18.02,
        111: 18.41,
        112: 18.81,
        113: 19.2,
        114: 19.6,
        115: 19.99,
        116: 20.39,
        117: 20.79,
        118: 21.19,
        119: 21.58,
        120: 21.98,
        121: 22.38,
        122: 22.78,
        123: 23.18,
        124: 23.59,
        125: 23.99,
        126: 24.39,
        127: 24.8,
        128: 25.2,
        129: 25.61,
        130: 26.02,
        131: 26.43,
        132: 26.84,
        133: 27.25,
        134: 27.66,
        135: 28.08,
        136: 28.5,
        137: 28.91,
        138: 29.33,
        139: 29.76,
        140: 30.18,
        141: 30.6,
        142: 31.03,
        143: 31.46,
        144: 31.89,
        145: 32.32,
        146: 32.76,
        147: 33.2,
        148: 33.64,
        149: 34.08,
        150: 34.53,
        151: 34.97,
        152: 35.42,
        153: 35.88,
        154: 36.33,
        155: 36.79,
        156: 37.25,
        157: 37.72,
        158: 38.18,
        159: 38.66,
        160: 39.13,
        161: 39.61,
        162: 40.09,
        163: 40.57,
        164: 41.06,
        165: 41.56,
        166: 42.05,
        167: 42.56,
        168: 43.06,
        169: 43.57,
        170: 44.09,
        171: 44.61,
        172: 45.13,
        173: 45.66,
        174: 46.19,
        175: 46.73,
        176: 47.28,
        177: 47.83,
        178: 48.39,
        179: 48.95,
        180: 49.52,
        181: 50.09,
        182: 50.68,
        183: 51.27,
        184: 51.86,
        185: 52.47,
        186: 53.08,
        187: 53.7,
        188: 54.33,
        189: 54.96,
        190: 55.61,
        191: 56.26,
        192: 56.93,
        193: 57.6,
        194: 58.28,
        195: 58.98,
        196: 59.68,
        197: 60.4,
        198: 61.13,
        199: 61.87,
        200: 62.63,
        201: 63.39,
        202: 64.17,
        203: 64.97,
        204: 65.78,
        205: 66.61,
        206: 67.46,
        207: 68.32,
        208: 69.2,
        209: 70.1,
        210: 71.02,
        211: None,
        212: None,
        213: None,
        214: None,
        215: None,
        216: None,
        217: None,
        218: None,
        219: None,
        220: None,
        221: None,
        222: None,
        223: 85,
        224: None,
        225: None,
        226: None,
        227: None,
        228: None,
        229: None,
        230: None,
        231: None,
        232: None,
        233: None,
        234: None,
        235: None,
        236: None,
        237: None,
        238: None,
        239: None,
        240: None,
        241: None,
        242: None,
        243: None,
        244: None,
        245: None,
        246: None,
        247: None,
        248: None,
        249: None,
        250: None,
        251: None,
        252: None,
        253: None,
        254: None,
        255: None,
    }

    def __init__(self, portstring, portspeed):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.mPort = connections.Connection.getConnection('serial', portstring, portspeed)
        self.portLock = connections.Connection.getLock(self.mPort)
        self.mPort.timeout = 0.05
        self.setAckPolicy(1)  # set ACK policy
        self.multipleMoveData = []
        self.mIDs = []

    """
    * @example HerkuleX
    *
    * Initialize servos.
    *
    * 1. clearError()
    * 2. torqueON(BROADCAST_ID)
    """
    def initialize(self, servoId=None):
        sId = servoId or HerkuleX.BROADCAST_ID

        try:
            time.sleep(0.100)
            self.clearError(sId)  # clear error for servo
            time.sleep(0.010)
            self.torqueON(sId)  # torqueON for servo
            time.sleep(0.010)
        except:
            self._logger.error(sys.exc_info()[0])

    """
    * @example HerkuleX_Get_IDs
    *
    * Get connected servos'ID
    *
    * Byte (-128~127) in Java
    * In terms of that Processing is running on PC,
    * there is no memory problem.
    * In this reason, this return type is Integer array.
    *
    * @return ArrayList<Integer> - Servo IDs
    """
    def performIDScan(self):
        self.mIDs = []

        for i in range(0, 254):
            if self.getPosition(i) != -1:
                self.mIDs.append(i)

        return self.mIDs

    """
    * Set Ack Policy
    *
    * @param valueACK 0=No Reply, 1=Only reply to READ CMD, 2=Always reply
    """
    def setAckPolicy(self, valueACK):
        if valueACK < 0 or valueACK > 2:
            return

        optData = [0] * 3
        optData[0] = 0x01  # Address
        optData[1] = 0x01  # Length
        optData[2] = valueACK  # Value. 0=No Replay, 1=Only reply to READ CMD, 2=Always reply

        packetBuf = self.buildPacket(0xFE, HerkuleX.HRAMWRITE, optData)
        self.sendData(packetBuf)

    """
     * Error clear
     *
     * @param servoID 0 ~ 254 (0x00 ~ 0xFE), 0xFE : BROADCAST_ID
     """
    def clearError(self, servoID):
        optData = [0] * 4
        optData[0] = 0x30  # Address
        optData[1] = 0x02  # Length
        optData[2] = 0x00  # Write error=0
        optData[3] = 0x00  # Write detail error=0

        packetBuf = self.buildPacket(servoID, HerkuleX.HRAMWRITE, optData)
        self.sendData(packetBuf)

    """
    * Get servo voltage
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    * @return current voltage 0 ~ 18.9 (-1: failure)
    """
    def getVoltage(self, servoID):
        optData = [0] * 2
        optData[0] = 0x36  # Address
        optData[1] = 0x01  # Length

        packetBuf = self.buildPacket(servoID, HerkuleX.HRAMREAD, optData)
        readBuf = self.sendDataForResult(packetBuf)

        if not self.isRightPacket(readBuf):
            return -1

#         if len(readBuf) < 10:
#             print "getVoltage: %s" % [str(x) for x in readBuf]
#             return -1

        if len(readBuf) < 11:
            self._logger.error("Strange Packet, expected len=11: %s", [str(x) for x in readBuf])
            return -1
        adc = ((readBuf[10] & 0x03) << 8) | (readBuf[9] & 0xFF)
        return round(adc * 0.074, 2)  # return ADC converted back to voltage

    """
    * Get servo voltage
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    * @return current temperature -80 ~ 5000 (-1: failure)
    """
    def getTemperature(self, servoID):
        optData = [0] * 2
        optData[0] = 0x37  # Address
        optData[1] = 0x01  # Length

        packetBuf = self.buildPacket(servoID, HerkuleX.HRAMREAD, optData)
        readBuf = self.sendDataForResult(packetBuf)

        if not self.isRightPacket(readBuf):
            return -1

        if len(readBuf) < 11:
            self._logger.error("Strange Packet, expected len=11: %s", [str(x) for x in readBuf])
            return -1
        adc = ((readBuf[10] & 0x03) << 8) | (readBuf[9] & 0xFF)
        if adc <= 0xFF:
            temp = HerkuleX.T_ADC.get(adc, None)
        else:
            return -1
        #The temperature chart after 210 is corrupted in the manual, guestimate the temperature assuming
        #a linear increase based on the two known values
        return temp if temp else round(((adc - 210) * 1.0754) + 71.02, 2)

    """
    * Get servo torque
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    * @return current torque 0 ~ 1023 (-1: failure)
    """
    def getTorque(self, servoID):
        optData = [0] * 2
        optData[0] = 0x40  # Address
        optData[1] = 0x01  # Length

        packetBuf = self.buildPacket(servoID, HerkuleX.HRAMREAD, optData)
        readBuf = self.sendDataForResult(packetBuf)

        if not self.isRightPacket(readBuf):
            return -1

        if len(readBuf) < 11:
            self._logger.error("Strange Packet, expected len=11: %s", [str(x) for x in readBuf])
            return -1
        return ((readBuf[10] & 0x03) << 8) | (readBuf[9] & 0xFF)  # return torque

    """
    * Torque ON
    *
    * @param servoID 0 ~ 254 (0x00 ~ 0xFE), 0xFE : BROADCAST_ID
    """
    def torqueON(self, servoID):
        optData = [0] * 3
        optData[0] = 0x34  # Address
        optData[1] = 0x01  # Length
        optData[2] = 0x60  # 0x60=Torque ON

        packetBuf = self.buildPacket(servoID, HerkuleX.HRAMWRITE, optData)
        self.sendData(packetBuf)

    """
    * Torque OFF
    *
    * @param servoID 0 ~ 254 (0x00 ~ 0xFE), 0xFE : BROADCAST_ID
    """
    def torqueOFF(self, servoID):
        optData = [0] * 3
        optData[0] = 0x34  # Address
        optData[1] = 0x01  # Length
        optData[2] = 0x00  # 0x60=Torque ON

        packetBuf = self.buildPacket(servoID, HerkuleX.HRAMWRITE, optData)
        self.sendData(packetBuf)

    """
    * @example HerkuleX_Infinite_Turn
    *
    * Move one servo with continous rotation
    *
    * @param servoID 0 ~ 254 (0x00 ~ 0xFE), 0xFE : BROADCAST_ID
    * @param goalSpeed -1023 ~ 1023 [CW:Negative Value(-), CCW:Positive Value(+)]
    * @param playTime 0 ~ 2856ms
    * @param led HerkuleX.LED_RED | HerkuleX.LED_GREEN | HerkuleX.LED_BLUE
    """
    def moveSpeedOne(self, servoID, goalSpeed, playTime, led):
        if goalSpeed > 1023 or goalSpeed < -1023:
            return  # speed (goal) non correct
        if playTime < 0  or playTime > 2856:
            return

        if goalSpeed < 0:
            goalSpeedSign = (-1) * goalSpeed
            goalSpeedSign |= 0x4000
        else:
            goalSpeedSign = goalSpeed

        speedGoalLSB = goalSpeedSign & 0X00FF  # MSB speedGoal
        speedGoalMSB = (goalSpeedSign & 0xFF00) >> 8  # LSB speedGoal

        playTime = playTime / 11.2  # ms --> value
        led = led | 0x02  # Speed Ctrl Mode

        optData = [0] * 5
        optData[0] = playTime  # Execution time
        optData[1] = speedGoalLSB
        optData[2] = speedGoalMSB
        optData[3] = led
        optData[4] = servoID

        packetBuf = self.buildPacket(servoID, HerkuleX.HSJOG, optData)
        self.sendData(packetBuf)

    """
    * @example HerkuleX_Infinite_Turn
    *
    * Get current servo speed (-1023 ~ 1023)
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    * @return current speed -1023 ~ 1023 [CW:Negative Value(-), CCW:Positive Value(+)]
    """
    def getSpeed(self, servoID):
        if servoID == 0xFE:
            return 0

        optData = [0] * 2
        optData[0] = 0x40  # Address
        optData[1] = 0x02  # Length

        packetBuf = self.buildPacket(servoID, HerkuleX.HRAMREAD, optData)
        readBuf = self.sendDataForResult(packetBuf)

        if not self.isRightPacket(readBuf):
            return -1

        if len(readBuf) < 11:
            self._logger.error("Strange Packet, expected len=11: %s", [str(x) for x in readBuf])
            return -1

        speedy = ((readBuf[10] & 0x03) << 8) | (readBuf[9] & 0xFF)

        if (readBuf[10] & 0x40) == 0x40:
            speedy *= -1

        return speedy

    """
    * @example HerkuleX_Pos_Ctrl
    *
    * Move one servo at goal position 0 - 1023
    *
    * @param servoID 0 ~ 254 (0x00 ~ 0xFE), 0xFE : BROADCAST_ID
    * @param goalPos 0 ~ 1023
    * @param playTime 0 ~ 2856ms
    * @param led HerkuleX.LED_RED | HerkuleX.LED_GREEN | HerkuleX.LED_BLUE
    """
    def moveOne(self, servoID, goalPos, playTime, led=0):
        if goalPos > 1023 or goalPos < 0:
            self._logger.warning("Got out of range position: %s", goalPos)
            return  # speed (goal) non correct
        if playTime < 0 or playTime > HerkuleX.MAX_PLAY_TIME:
            self._logger.warning("Got out of range playtime: %s", playTime)
            return

        # Position definition
        posLSB = goalPos & 0X00FF  # MSB Pos
        posMSB = (goalPos & 0XFF00) >> 8  # LSB Pos
        playTimeVal = int(round(playTime / 11.2))  # ms --> value
        led = led & 0xFD  # Pos Ctrl Mode

        self._logger.debug("Moving %s to %s in %sms" % (servoID, goalPos, playTime))

        optData = [0] * 5
        optData[0] = playTimeVal  # Execution time in ms / 11.2
        optData[1] = posLSB
        optData[2] = posMSB
        optData[3] = led
        optData[4] = servoID

        packetBuf = self.buildPacket(servoID, HerkuleX.HSJOG, optData)
        self.sendData(packetBuf)
        #self._logger.debug(self.error_text(servoID))

    """
    * Get servo position
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    * @return current position 0 ~ 1023 (-1: failure)
    * @example HerkuleX_Pos_Ctrl
    """
    def getPosition(self, servoID):
        if servoID == 0xFE:
            return -1

        optData = [0] * 2
        optData[0] = 0x3A  # Address
        optData[1] = 0x02  # Length

        packetBuf = self.buildPacket(servoID, HerkuleX.HRAMREAD, optData)
        readBuf = self.sendDataForResult(packetBuf)

        if not self.isRightPacket(readBuf):
            return -1

        if len(readBuf) < 11:
            self._logger.error("Strange Packet, expected len=11: %s", [str(x) for x in readBuf])
            self._logger.error("Sent packet: %s", [str(x) for x in packetBuf])
            return -1
        pos = ((readBuf[10] & 0x03) << 8) | (readBuf[9] & 0xFF)
        return pos

    """
    * Move one servo to an angle between -167 and 167
    *
    * @param servoID 0 ~ 254 (0x00 ~ 0xFE), 0xFE : BROADCAST_ID
    * @param angle -166 ~ 166 degrees
    * @param playTime 0 ~ 2856 ms
    * @param led HerkuleX.LED_RED | HerkuleX.LED_GREEN | HerkuleX.LED_BLUE
    """
    def moveOneAngle(self, servoID, angle, playTime, led):
        if angle > 167.0 or angle < -167.0:
            return
        position = (angle / 0.325) + 512
        self.moveOne(servoID, position, playTime, led)

    """
    * Get servo position in degrees
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    * @return current angle -166.7 ~ 166.7 degrees
    """
    def getAngle(self, servoID):
        pos = self.getPosition(servoID)
        if pos < 0:
            return -1
        return (pos - 512) * 0.325

    """
    * @HerkuleX_Unison_Movement
    *
    * Add one servo movement data
    *
    * ex)  addMove(0, 512, HerkuleX.LED_RED)
    *        addMove(1, 235, HerkuleX.LED_GREEN)
    *        addMove(2, 789, HerkuleX.LED_BLUE)
    *        actionAll(1000)
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    * @param goal 0 ~ 1023
    * @param led HerkuleX.LED_RED | HerkuleX.LED_GREEN | HerkuleX.LED_BLUE
    """
    def addMove(self, servoID, goal, led):
        if goal > 1023 or goal < 0:
            return  # 0 <--> 1023 range

        # Position definition
        posLSB = goal & 0X00FF  # MSB Pos
        posMSB = (goal & 0XFF00) >> 8  # LSB Pos
        led = led & 0xFD  # Pos Ctrl Mode

        optData = [0] * 4
        optData[0] = posLSB
        optData[1] = posMSB
        optData[2] = led
        optData[3] = servoID

        self.addData(optData)  # add servo data to list, pos mode

    """
    * @example HerkuleX_Unison_Movement
    *
    * Add one servo movement data in degrees
    *
    * ex)  addAngle(0, -90.5f, HerkuleX.LED_RED)
    *        addAngle(1, 0, HerkuleX.LED_BLUE)
    *        addAngle(2, 90.5f, HerkuleX.LED_GREEN)
    *        actionAll(1000)
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    * @param angle -167 ~ 167 degrees
    * @param led HerkuleX.LED_RED | HerkuleX.LED_GREEN | HerkuleX.LED_BLUE
    """
    def addAngle(self, servoID, angle, led):
        if angle > 167.0 or angle < -167.0:
            return  # out of the range
        position = (angle / 0.325) + 512
        self.addMove(servoID, position, led)

    """
    * @example HerkuleX_Unison_Movement
    *
    * Add one servo infinite turn speed data
    *
    * ex)  addSpeed(0, 512, HerkuleX.LED_RED)
    *        addSpeed(1, -512, HerkuleX.LED_GREEN)
    *        addSpeed(2, -300, HerkuleX.LED_BLUE)
    *        actionAll(1000)
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    * @param goalSpeed -1023 ~ 1023 [CW:Negative Value(-), CCW:Positive Value(+)]
    * @param led HerkuleX.LED_RED | HerkuleX.LED_GREEN | HerkuleX.LED_BLUE
    """
    def addSpeed(self, servoID, goalSpeed, led):
        if goalSpeed > 1023 or goalSpeed < -1023:
            return  # speed (goal) non correct

        if goalSpeed < 0:
            goalSpeedSign = (-1) * goalSpeed
            goalSpeedSign |= 0x4000
        else:
            goalSpeedSign = goalSpeed

        speedGoalLSB = goalSpeedSign & 0X00FF  # MSB speedGoal
        speedGoalMSB = (goalSpeedSign & 0xFF00) >> 8  # LSB speedGoal

        led = led | 0x02  # Speed Ctrl Mode

        optData = [0] * 4
        optData[0] = speedGoalLSB
        optData[1] = speedGoalMSB
        optData[2] = led
        optData[3] = servoID

        self.addData(optData)  # add servo data to list, speed mode

    # add data to variable list servo for syncro execution
    def addData(self, optData):
        if len(self.multipleMoveData) >= 4 * 53:  # A SJOG can deal with only 53 motors at one time.
            return

        for i in range(0, len(optData)):
            self.multipleMoveData.append(optData[i])

    """
    * @example HerkuleX_Unison_Movement
    *
    * Move(Turn) all servos with the same execution time
    *
    * ex)  addMove(0, 512, HerkuleX.LED_RED)
    *         addAngle(1, 90.5f, HerkuleX.LED_GREEN)
    *         addSpeed(2, -300, HerkuleX.LED_BLUE)
    *         actionAll(1000)
    *
    * @param playTime 0 ~ 2865 ms
    """
    def actionAll(self, playTime):
        if playTime < 0 or playTime > 2856:
            return

        optDataSize = len(self.multipleMoveData)
        if optDataSize < 4:
            return

        optData = [0] * optDataSize + 1

        optData[0] = playTime
        for i in range(0, optDataSize):
            optData[i + 1] = self.multipleMoveData[i]

        packetBuf = self.buildPacket(0xFE, HerkuleX.HSJOG, optData)
        self.sendData(packetBuf)

        self.multipleMoveData.clear()

    """
    * LED Control -  GREEN, BLUE, RED
    *
    * @param servoID 0 ~ 254 (0x00 ~ 0xFE), 0xFE : BROADCAST_ID
    * @param led HerkuleX.LED_RED | HerkuleX.LED_GREEN | HerkuleX.LED_BLUE
    """
    def setLed(self, servoID, led):
        optData = [0] * 3
        optData[0] = 0x35  # Address
        optData[1] = 0x01  # Length

        led2 = 0x00
        if (led & HerkuleX.LED_GREEN) == HerkuleX.LED_GREEN:
            led2 |= 0x01
        if (led & HerkuleX.LED_BLUE) == HerkuleX.LED_BLUE:
            led2 |= 0x02
        if (led & HerkuleX.LED_RED) == HerkuleX.LED_RED:
            led2 |= 0x04

        optData[2] = led2
        packetBuf = self.buildPacket(servoID, HerkuleX.HRAMWRITE, optData)
        self.sendData(packetBuf)


    """
    * Reboot single servo
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    """
    def reboot(self, servoID):
        if servoID == 0xFE:
            return

        packetBuf = self.buildPacket(servoID, HerkuleX.HREBOOT, None)
        self.sendData(packetBuf)


    """
    * Revert single servo to factory defaults
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    """
    def rollback(self, servoID):
        if servoID == 0xFE:
            return

        packetBuf = self.buildPacket(servoID, HerkuleX.HROLLBACK, None)
        self.sendData(packetBuf)


    """
    * Servo Status
    *
    * @param servoID 0 ~ 253 (0x00 ~ 0xFD)
    * @return     servo status
    *     H_STATUS_OK                 = 0x00
    *     H_ERROR_INPUT_VOLTAGE         = 0x01
    *     H_ERROR_POS_LIMIT            = 0x02
    *     H_ERROR_TEMPERATURE_LIMIT    = 0x04
    *     H_ERROR_INVALID_PKT            = 0x08
    *     H_ERROR_OVERLOAD            = 0x10
    *     H_ERROR_DRIVER_FAULT          = 0x20
    *     H_ERROR_EEPREG_DISTORT        = 0x40
    """
    def stat(self, servoID, detail=False):
        if servoID == 0xFE:
            if detail:
                return (0x00, 0x00)
            return 0x00

        packetBuf = self.buildPacket(servoID, HerkuleX.HSTAT, None)
        readBuf = self.sendDataForResult(packetBuf)

        if not self.isRightPacket(readBuf):
            if detail:
                return (-1, 0x00)
            return -1

        if detail:
            return (readBuf[7], readBuf[8])  # return status
        else:
            return readBuf[7]

    def error_text(self, servoID):
        statusCode, detailCode = self.stat(servoID, True)

        if statusCode <= -1:
            return ['Invalid response recieved, unknown status', ]

        if statusCode & HerkuleX.H_STATUS_OK == HerkuleX.H_STATUS_OK:
            return []

        codes = []
        if statusCode & HerkuleX.H_ERROR_INPUT_VOLTAGE == HerkuleX.H_ERROR_INPUT_VOLTAGE:
            codes.append('Exceeded Input Voltage')
        if statusCode & HerkuleX.H_ERROR_POS_LIMIT == HerkuleX.H_ERROR_POS_LIMIT:
            codes.append('Exceeded Position Limit')
        if statusCode & HerkuleX.H_ERROR_TEMPERATURE_LIMIT == HerkuleX.H_ERROR_TEMPERATURE_LIMIT:
            codes.append('Exceeded Temperature Limit')
        if statusCode & HerkuleX.H_ERROR_INVALID_PKT == HerkuleX.H_ERROR_INVALID_PKT:
            details = []
            if detailCode & HerkuleX.H_PKTERR_CHECKSUM == HerkuleX.H_PKTERR_CHECKSUM:
                details.append('Checksum Error')
            if detailCode & HerkuleX.H_PKTERR_UNKNOWN_CMD == HerkuleX.H_PKTERR_UNKNOWN_CMD:
                details.append('Unknown Command')
            if detailCode & HerkuleX.H_PKTERR_EXCEED_REG_RANGE == HerkuleX.H_PKTERR_EXCEED_REG_RANGE:
                details.append('Exceed REG range')
            if detailCode & HerkuleX.H_PKTERR_GARBAGE == HerkuleX.H_PKTERR_GARBAGE:
                details.append('Garbage detected')
            codes.append('Invalid Packet Recieved: %s' % details)
        if statusCode & HerkuleX.H_ERROR_OVERLOAD == HerkuleX.H_ERROR_OVERLOAD:
            codes.append('Overload')
        if statusCode & HerkuleX.H_ERROR_DRIVER_FAULT == HerkuleX.H_ERROR_DRIVER_FAULT:
            codes.append('Driver Fault')
        if statusCode & HerkuleX.H_ERROR_EEPREG_DISTORT == HerkuleX.H_ERROR_EEPREG_DISTORT:
            codes.append('EEP Registry Distorted')

        return codes

    """
    * Model
    *
    * @param servoID
    * @return 1 = DRS-0101, 2 = DRS-0201
    """
    def model(self, servoID):
        optData = [0] * 2
        optData[0] = 0x00  # Address
        optData[1] = 0x01  # Length

        packetBuf = self.buildPacket(servoID, HerkuleX.HEEPREAD, optData)

        readBuf = self.sendDataForResult(packetBuf)

        if not self.isRightPacket(readBuf):
            return -1

        return readBuf[8]  # return model

    """
    * @example HerkuleX_Set_ID
    *
    * setID
    *
    *   CAUTION - If there are duplicated servo IDs on your Serial Line,It does not work.
    *           When you change your servo's ID, make sure there is only the servo on the line if possible.
    *
    * @param ID_Old
    * @param ID_New
    * @return true - success, false - failure
    *
    """
    def set_ID(self, ID_Old, ID_New):
        if ID_Old == 0xFE or ID_New == 0xFE or ID_Old == ID_New:
            return False

        if self.getPosition(ID_Old) == -1:
            return False

        optData = [0] * 3
        optData[0] = 0x06  # Address
        optData[1] = 0x01  # Length
        optData[2] = ID_New

        packetBuf = self.buildPacket(ID_Old, HerkuleX.HEEPWRITE, optData)
        self.sendData(packetBuf)

        self.reboot(ID_Old)
        return True

    """
    * Write registry in the RAM: one byte
    *
    * See. HerkuleX Manual.
    *
    * @param servoID
    * @param address
    * @param writeByte
    *
    """
    def writeRegistryRAM(self, servoID, address, writeByte):
        length = 1 + (writeByte > 255)
        optData = [0] * (2 + length)
        optData[0] = address  # Address
        optData[1] = length  # Length
        if length == 1:
            optData[2] = writeByte
        else:
            optData[2] = writeByte & 0X00FF
            optData[3] = (writeByte & 0XFF00) >> 8

        packetBuf = self.buildPacket(servoID, HerkuleX.HRAMWRITE, optData)
        self.sendData(packetBuf)

    """
    * write registry in the EEP memory (ROM): one byte
    *
    * See. HerkuleX Manual.
    *
    * CAUTION : If you are not familiar with HerekuleX servo yet,
    *              Use HerkuleX Manager Instead.
    *
    * @param servoID
    * @param address
    * @param writeByte
    *
    """
    def writeRegistryEEP(self, servoID, address, writeByte, length=1):
        if length == None:
            length = 1 + (writeByte > 255)
        optData = [0] * (2 + length)
        optData[0] = address  # Address
        optData[1] = length  # Length
        if length == 1:
            optData[2] = writeByte
        else:
            optData[2] = writeByte & 0X00FF
            optData[3] = (writeByte & 0XFF00) >> 8

        packetBuf = self.buildPacket(servoID, HerkuleX.HEEPWRITE, optData)
        self.sendData(packetBuf)

    def isRightPacket(self, buf):
        if len(buf) < 7:
            # print [str(x) for x in buf]
            return False
        if len(buf) != buf[2]:
            self._logger.warning("Invalid packet! %s", [str(x) for x in buf])
            return False

        chksum1 = self.checksum1(buf)  # Checksum1
        chksum2 = self.checksum2(chksum1)  # Checksum2

        if chksum1 != buf[5]:
            # print [str(x) for x in buf]
            return False
        if chksum2 != buf[6]:
            # print [str(x) for x in buf]
            return False

        return True

    # build packet
    def buildPacket(self, pId, cmd, optData):
        if optData == None:
            pktSize = HerkuleX.BASIC_PKT_SIZE
        else:
            pktSize = HerkuleX.BASIC_PKT_SIZE + len(optData)

        packetBuf = [0] * pktSize

        packetBuf[0] = 0xFF  # Packet Header
        packetBuf[1] = 0xFF  # Packet Header
        packetBuf[2] = pktSize  # Packet Size
        packetBuf[3] = pId  # Servo ID
        packetBuf[4] = cmd  # Command

        for i in range(0, pktSize - HerkuleX.BASIC_PKT_SIZE):
            packetBuf[7 + i] = optData[i]

        packetBuf[5] = self.checksum1(packetBuf)  # Checksum 1
        packetBuf[6] = self.checksum2(packetBuf[5])  # Checksum 2

        return packetBuf

    # checksum1
    def checksum1(self, buf):
        chksum1 = 0x00

        for i in range(0, len(buf)):
            if i == 0 or i == 1 or i == 5 or i == 6:
                continue
            chksum1 ^= buf[i]

        return chksum1 & 0xFE

    # checksum2
    def checksum2(self, chksum1):
        return (~chksum1) & 0xFE

    def sendData(self, buf):
        with self.portLock:
            self._logger.log(1, "Sending packet: [%s]" % ', '.join([str(x) for x in buf]))
            packet = ''.join([chr(x) for x in buf])
            self.mPort.write(packet)

    def sendDataForResult(self, buf):
        with self.portLock:
            self.mPort.flushInput()
            self._logger.log(1, "Sending packet: %s", [str(x) for x in buf])
            self.sendData(buf)
            ackDelay = HerkuleX.WAIT_TIME_BY_ACK / 1000.0

            #try:
            #    time.sleep(ackDelay)
            #except:
            #    self._logger.error(sys.exc_info()[0])
            #readBuf = []
            #while self.mPort.inWaiting() > 0:
            #    inBuffer = self.mPort.read(1)
            #    readBuf.append(ord(inBuffer) & 0xFF)

            # Locate the start of the header
            readBuf = [0xFF, 0xFF]
            startTime = time.time()
            while time.time() - startTime < self.mPort.timeout + ackDelay:
                inBuffer = self.mPort.read(1)
                if len(inBuffer) == 0:
                    continue
                byte = ord(inBuffer) & 0xFF
                if byte > 0xE9: #max valid packet length
                    continue
                readBuf.append(byte)
                break

            if len(readBuf) > 2:
                inBuffer = self.mPort.read(readBuf[2] - 3)
                [readBuf.append(ord(c) & 0xFF) for c in inBuffer]

            if len(readBuf) > 2 and len(readBuf) < readBuf[2] and self.mPort.inWaiting():
                self._logger.warning("Not all bytes received before timeout!")
                inBuffer = self.mPort.read(min(self.mPort.inWaiting(), readBuf[2] - len(readBuf)))

        if len(readBuf) == 2:
            readBuf = []
            self._logger.warning("No data received before timeout! Send packet: %s", [str(x) for x in buf])
        self._logger.log(1, "Received packet: [%s]" % ', '.join([str(x) for x in readBuf]))

        return readBuf


if __name__ == '__main__':
    h = HerkuleX('COM15', 115200)
    ids = h.performIDScan()
    for sid in ids:
        h.reboot(sid)
        h.clearError(sid)
        h.torqueOFF(sid)
    while(True):
        msg = ''
        for sid in ids:
#             msg += "%s - Position: %s, Torque: %s, Voltage: %s\n" % (sid, h.getPosition(sid), h.getTorque(sid), h.getVoltage(sid))
            msg += "%s - Position: %s\n" % (sid, h.getPosition(sid))
        print msg
#         time.sleep(0.01)
