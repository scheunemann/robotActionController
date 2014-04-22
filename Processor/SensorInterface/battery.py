from connections import Connection


class BatteryLevelSensor(object):
    sensorType = 'HERKULEX_BATTERY'

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
        self._externalId = sensor.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("HerkuleX voltage sensor %s is missing its external Id!", sensor.name)
            raise ValueError()
        self._externalId = int(self._externalId)

        port = config.port
        speed = config.portSpeed

        self._conn = Connection.getConnection("HERKULEX", port, speed)
        self._conn.initialize(self._externalId)

    def getCurrentValue(self):
        rawValue = self._conn.getVoltage(self._externalId)

        if rawValue:
            return BatteryLevelSensor.calculatePercentage(rawValue)

        return None

    @staticmethod
    def calculatePercentage(voltage):
        vals = BatteryLevelSensor.CHARGELEVELS[:]
        vals.sort(key=lambda vp: abs(vp[0] - voltage))
        vals = vals[0:2]
        vals.sort(key=lambda vp: vp[0])
        minVolt, minPct = vals[0]
        maxVolt, maxPct = vals[1]
        pct = minPct + (maxPct - minPct) * ((voltage - minVolt) / (maxVolt - minVolt))
        return min(100, max(0, round(pct, 2)))

if __name__ == '__main__':
    for i in range(0, 37):
        voltage = 10.0 + (i / 10.0)
        percentage = BatteryLevelSensor.calculatePercentage(voltage)
        print "%sv = %spct" % (voltage, percentage)
