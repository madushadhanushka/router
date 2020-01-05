import math

class Track:
	def __init__(self, latitude, longitude, track_id):
		self.latitude = latitude
		self.longitude = longitude
		self.track_id = track_id

	def printCoordinate(self):
		print('latitude: ' + str(self.latitude) + ' longitude: '+ str(self.longitude))

	def findDistance(self, coordinate2):
		return math.sqrt((self.latitude - coordinate2.latitude)**2 + (self.longitude - coordinate2.longitude)**2)