import math

class ZoneSegment:
    def __init__(self, latitude, longitude, acc_x, acc_y, data_mean, data_std):
        self.latitude = latitude
        self.longitude = longitude
        self.acc_x = acc_x
        self.acc_y = acc_y
        self.data_mean = data_mean
        self.data_std = data_std

    def findDistance(self, coordinate2):
        return math.sqrt((self.latitude - coordinate2.latitude) ** 2 + (self.longitude - coordinate2.longitude) ** 2)