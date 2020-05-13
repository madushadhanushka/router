import mysql.connector
from datetime import datetime
from models.track import Track
from models.zone_segment import ZoneSegment

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="root",
    database="router"
)
mycursor = mydb.cursor()

def getCurrentGoal():
	mycursor.execute("SELECT meta_value FROM meta_data WHERE meta_key='current_goal'")
	return int(mycursor.fetchall()[0][0])

def updateCurrentGoal(current_goal):
    if current_goal is None:
        current_goal = 0
    print("Update current goal as: " + str(current_goal))
    mycursor.execute("UPDATE meta_data SET meta_value=%s WHERE meta_key='current_goal'", (current_goal,))
    mydb.commit()
    return

def findReverseRoute(current_route):
    mycursor.execute("SELECT reverse_route from reverse_route where route=%s", (current_route,))
    return int(mycursor.fetchall()[0][0])

def findMaxGoal(current_route):

    time_type = find_time_type()
    print("Time type selected as: " + str(time_type))
    mycursor.execute("SELECT goal_id, count FROM link_goal_model where link_id=%s and time_type=%s", (current_route, time_type))
    initialGoalList = mycursor.fetchall()
    print(mycursor.statement)
    print(initialGoalList)
    maxGoalCount = 0
    maxGoalId = 0
    for goals in initialGoalList:
        if maxGoalCount < goals[1]:
            maxGoalCount = goals[1]
            maxGoalId = goals[0]
    return maxGoalId, maxGoalCount

def findMaxLink(current_link, current_goal):

    time_type = find_time_type()
    mycursor.execute("SELECT route_to, count from route_map_model WHERE route_from=%s AND current_goal=%s AND time_type=%s", (current_link, current_goal, time_type))
    link_list = mycursor.fetchall()
    print(mycursor.statement)
    print(link_list)
    max_link_count = 0
    max_link_id = 0
    for links in link_list:
        if max_link_count < links[1]:
            max_link_count = links[1]
            max_link_id = links[0]

    if max_link_id == 0:
        mycursor.execute("SELECT route_to, count from route_map_model WHERE route_from=%s AND time_type=%s", (current_link, time_type))
        link_list2 = mycursor.fetchall()
        print(mycursor.statement)
        max_link_count2 = 0
        max_link_id = 0
        for links in link_list2:
            if max_link_count2 < links[1]:
                max_link_count2 = links[1]
                max_link_id = links[0]
    return max_link_id

def resetGoalRecord():
    mycursor.execute("UPDATE meta_data SET meta_value=0 WHERE meta_key='current_goal'")
    mydb.commit()

# Shortest distance (angular) between two angles.
# It will be in range [0, 180].
def findAcuteAngle(alpha, beta):
    phi = abs(beta - alpha) % 360
    if phi > 180:
        return 360 - phi
    else:
        return phi

def find_time_type():

    #todo time type hardcode to type 1
    return 1

    current_time = datetime.now()
    mycursor.execute("SELECT meta_value FROM meta_data WHERE meta_key='time_range_1_min'")
    time_range_1_min = datetime.strptime(mycursor.fetchall()[0][0], '%H:%M:%S')

    mycursor.execute("SELECT meta_value FROM meta_data WHERE meta_key='time_range_1_max'")
    time_range_1_max = datetime.strptime(mycursor.fetchall()[0][0], '%H:%M:%S')

    mycursor.execute("SELECT meta_value FROM meta_data WHERE meta_key='time_range_2_min'")
    time_range_2_min = datetime.strptime(mycursor.fetchall()[0][0], '%H:%M:%S')

    mycursor.execute("SELECT meta_value FROM meta_data WHERE meta_key='time_range_2_max'")
    time_range_2_max = datetime.strptime(mycursor.fetchall()[0][0], '%H:%M:%S')

    if isWeekDay(current_time):
        if time_in_range(time_range_1_min, time_range_1_max, current_time):
            return 1
        elif time_in_range(time_range_2_min, time_range_2_max, current_time):
            return 2
    else:
        return 3

def time_in_range(start, end, x):
    """Return true if x is in the range [start, end]"""
    start_time = datetime(1900, 1, 1, start.hour, start.minute, start.second, 0)
    end_time = datetime(1900, 1, 1, end.hour, end.minute, end.second, 0)
    x_time = datetime(1900, 1, 1, x.hour, x.minute, x.second, 0)

    if start_time <= end_time:
        return start_time <= x_time <= end_time
    else:
        return start_time <= x_time or x_time <= end_time

def isWeekDay(current_time):
    dayNumber = current_time.isoweekday()
    if dayNumber > 5:
        return False
    else:
        return True

def getLastCoordinates(count):
    mycursor.execute("SELECT acc_x, acc_y FROM coordinate order by id DESC LIMIT %s", (count,))
    return mycursor.fetchall()

def findClosedRouteSegment(currentCoordinate):
    mycursor.execute("SELECT latitude, longitude, acc_x_apms, acc_y_apms, safty_threshold, safty_sign from apms_zones")
    segments = mycursor.fetchall()
    mydb.commit()
    minDistance = float("inf")
    pivotCooridnate = ZoneSegment(0, 0, 0, 0, 0, 0)
    print(segments)
    for segment in segments:
        fixedPoint = ZoneSegment(segment[0], segment[1], segment[2], segment[3], segment[4], segment[5])
        distance = fixedPoint.findDistance(currentCoordinate)
        if distance < minDistance:
            minDistance = distance
            pivotCooridnate = fixedPoint
    return pivotCooridnate