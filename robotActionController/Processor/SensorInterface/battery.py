from robotActionController.connections import Connection


class BatteryLevelSensor(object):

    def __init__(self, sensor, config):
        self._externalId = sensor.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("HerkuleX voltage sensor %s is missing its external Id!", sensor.name)
            raise ValueError()
        self._externalId = int(self._externalId)

        port = config.port
        speed = config.portSpeed

        self._conn = Connection.getConnection("HERKULEX", port, speed)
        self._connLock = Connection.getLock(self._conn)
        with self._connLock:
            self._conn.initialize(self._externalId)

    def getCurrentValue(self):
        with self._connLock:
            rawValue = self._conn.getVoltage(self._externalId)

        if rawValue:
            return self.calculatePercentage(rawValue)

        return None

    def calculatePercentage(self, voltage):
        vals = self.chargeLevels[:]
        vals.sort(key=lambda vp: abs(vp[0] - voltage))
        vals = vals[0:2]
        vals.sort(key=lambda vp: vp[0])
        minVolt, minPct = vals[0]
        maxVolt, maxPct = vals[1]
        pct = minPct + (maxPct - minPct) * ((voltage - minVolt) / (maxVolt - minVolt))
        return min(100, max(0, round(pct, 2)))

class LeadAcidBatteryLevelSensor(BatteryLevelSensor):
    sensorType = 'HERKULEX_Pb_BATTERY'

    CHARGELEVELS = [
                    (12.70, 100),
                    (12.50, 90),
                    (12.42, 80),
                    (12.32, 70),
                    (12.20, 60),
                    (12.06, 50),
                    (11.90, 40),
                    (11.75, 30),
                    (11.58, 20),
                    (11.31, 10),
                    (10.50, 0),
                ]

    def __init__(self, sensor, config):
        super(LeadAcidBatteryLevelSensor, self).__init__(sensor, config)
        self.chargeLevels = LeadAcidBatteryLevelSensor.CHARGELEVELS


class LithiumPhosphateBatteryLevelSensor(BatteryLevelSensor):
    sensorType = 'HERKULEX_LiFe_BATTERY'

    CHARGELEVELS = [
                    (13.50, 100),
                    (12.55, 90),
                    (12.52, 80),
                    (12.48, 70),
                    (12.45, 60),
                    (12.40, 50),
                    (12.30, 40),
                    (12.25, 30),
                    (12.10, 20),
                    (11.60, 10),
                    (10.00, 0),
                ]

    def __init__(self, sensor, config):
        super(LithiumPhosphateBatteryLevelSensor, self).__init__(sensor, config)
        self.chargeLevels = LithiumPhosphateBatteryLevelSensor.CHARGELEVELS


if __name__ == '__main__':
    for i in range(0, 37):
        voltage = 10.0 + (i / 10.0)
        percentage = BatteryLevelSensor.calculatePercentage(voltage)
        print "%sv = %spct" % (voltage, percentage)
