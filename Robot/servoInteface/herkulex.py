"""
* HerkuleX
* A Python Processing library for Dongbu HerkuleX Servo adapted from:
* https://github.com/dongburobot/HerkuleXProcessing/
*
* This library is free software you can redistribute it and/or
* modify it under the terms of the GNU Lesser General Public
* License as published by the Free Software Foundation either
* version 2.1 of the License, or (at your option) any later version.
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
import serial 
import time
import logging

__all__ = ['HerkuleX', ]

class HerkuleX(object):
    
    """
    POS_SCALE = 0.325
    POS_OFFSET = 512
    SPEED_SCALE = (0.68 * steps) #nominal steps per second
    """
    
    BASIC_PKT_SIZE = 7
    WAIT_TIME_BY_ACK = 30
        
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
    
    def __init__(self, portstring, portspeed):
        self.mPort = serial.Serial(port=portstring, baudrate=portspeed)
        self.multipleMoveData = []
        self.mIDs = []
        self._logger = logging.getLogger(__name__)
    
    """
    * @example HerkuleX
    * 
    * Initialize servos.
    * 
    * 1. clearError()
    * 2. setAckPolicy(1)
    * 3. torqueON(BROADCAST_ID)
    """
    def initialize(self):
        try:
            time.sleep(0.100)
            self.clearError(HerkuleX.BROADCAST_ID)  # clear error for all servos
            time.sleep(0.010)
            self.setAckPolicy(1)  # set ACK policy
            time.sleep(0.010)
            self.torqueON(HerkuleX.BROADCAST_ID)  # torqueON for all servos
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
    * @param valueACK 0=No Replay, 1=Only reply to READ CMD, 2=Always reply
    """
    def setAckPolicy(self, valueACK):
        if valueACK < 0 or valueACK > 2:
            return
        
        optData = [0] * 3
        optData[0] = 0x34  # Address
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
        self.sendData(packetBuf)

        try:
            time.sleep(HerkuleX.WAIT_TIME_BY_ACK / 1000.0)
        except:
            self._logger.error(sys.exc_info()[0])
        
        readBuf = self.readData()
        
        if not self.isRightPacket(readBuf):
            return 0
       
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
            return  # speed (goal) non correct
        if playTime < 0 or playTime > 2856:
            return
        
        # Position definition
        posLSB = goalPos & 0X00FF  # MSB Pos
        posMSB = (goalPos & 0XFF00) >> 8  # LSB Pos
        playTime = int(round(playTime / 11.2))  # ms --> value
        led = led & 0xFD  # Pos Ctrl Mode
        
        optData = [0] * 5
        optData[0] = playTime  # Execution time    
        optData[1] = posLSB
        optData[2] = posMSB
        optData[3] = led
        optData[4] = servoID
        
        packetBuf = self.buildPacket(servoID, HerkuleX.HSJOG, optData)
        self.sendData(packetBuf)
    
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
        self.sendData(packetBuf)

        try:
            time.sleep(HerkuleX.WAIT_TIME_BY_ACK / 1000.0)
        except:
            self._logger.error(sys.exc_info()[0])
        
        readBuf = self.readData()
        
        if not self.isRightPacket(readBuf):
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
            return 0
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
    def stat(self, servoID):
        if servoID == 0xFE:
            return 0x00
        
        packetBuf = self.buildPacket(servoID, HerkuleX.HSTAT, None)
        self.sendData(packetBuf)
        
        try:
            time.sleep(HerkuleX.WAIT_TIME_BY_ACK / 1000.0)
        except:
            self._logger.error(sys.exc_info()[0])
        
        readBuf = self.readData()
        
        if not self.isRightPacket(readBuf):
            return -1

        return readBuf[7]  # return status
    
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
        self.sendData(packetBuf)
          
        try:
            time.sleep(HerkuleX.WAIT_TIME_BY_ACK / 1000.0)
        except:
            self._logger.error(sys.exc_info()[0])
         
        readBuf = self.readData()
        
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
        optData = [0] * 3
        optData[0] = address  # Address
        optData[1] = 0x01  # Length
        optData[2] = writeByte
        
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
    def writeRegistryEEP(self, servoID, address, writeByte):
        optData = [0] * 3
        optData[0] = address  # Address
        optData[1] = 0x01  # Length
        optData[2] = writeByte
        
        packetBuf = self.buildPacket(servoID, HerkuleX.HEEPWRITE, optData)
        self.sendData(packetBuf)
    
    def isRightPacket(self, buf):
        if len(buf) < 7:
            return False
        
        chksum1 = self.checksum1(buf)  # Checksum1
        chksum2 = self.checksum2(chksum1)  # Checksum2
        
        if chksum1 != buf[5]:
            return False
        if chksum2 != buf[6]:
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
        self.mPort.write(''.join([chr(x) for x in buf]))
    
    def readData(self):
        retBuf = []
        
        while self.mPort.inWaiting() > 0:
            inBuffer = self.mPort.read(1)
            retBuf.append(ord(inBuffer) & 0xFF)
        
        return retBuf

if __name__ == '__main__':
    h = HerkuleX('COM4', 115200)
    ids = h.performIDScan()
    for sid in ids:
        h.torqueOFF(sid)
    while(True):
        for sid in ids:
            print h.getPosition(sid)
        time.sleep(1)