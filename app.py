from flask import Flask, request
import mysql.connector
from models.track import Track
from pandas import DataFrame
from models.zone_segment import ZoneSegment
import pandas as pd
import numpy as np

from libs.utils import getCurrentGoal, updateCurrentGoal, findReverseRoute, findMaxGoal, findMaxLink, resetGoalRecord, findAcuteAngle, getLastCoordinates, findClosedRouteSegment, find_time_type

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="root",
    database="router"
)
mycursor = mydb.cursor()
app = Flask(__name__,  static_url_path='/static')


@app.route('/js/<path:path>')
def send_js(path):
    """
    Load javascript component for demo
    """
    return send_from_directory('js', path)

@app.route('/findGoal', methods=['POST'])
def findGoal():
    """Find goal and next link by current location

            Inputs:
                latitude (string): latitude of current location
                longitude (string): longitude of current location

            Returns:
                status: Execution status
                next_goal: Next goal prediction
                next_route: Next route prediction
    """
    input = request.get_json()
    print(input)
    currentRoot = findCurrentRoute(input['latitude'], input['longitude'], input['direction'])
    next_goal, next_route = findNextGoal(currentRoot, input['direction'])
    updateCurrentGoal(next_goal)
    return {"status": "success", "next_goal": next_goal, "next_route": next_route, "current_route": currentRoot}

@app.route('/coordinate', methods=['POST'])
def addCoordinateAPI():
    """Add geo point into the DB
    Inputs:
                latitude (string): latitude of current location
                longitude (string): longitude of current location

            Returns:
                status: Execution status
    """
    input = request.get_json()
    addCoordinate(input['latitude'], input['longitude'], input['track_id'], input['direction'], input['acc_x'], input['acc_y'], input['speed'])
    return {"status": "success"}

@app.route('/lastCoordinate', methods=['GET'])
def getLastCoordinate():
    mycursor.execute("SELECT latitude,longitude,direction FROM coordinate ORDER BY ID DESC LIMIT 1")
    lastCoordinate = mycursor.fetchall()
    print(lastCoordinate[0])
    return {
        "latitude": lastCoordinate[0][0],
        "longitude": lastCoordinate[0][1],
        "direction": lastCoordinate[0][2]

    }

@app.route('/resetGoal', methods=['POST'])
def resetGoal():
    """
    Set current goal to zero
    """
    resetGoalRecord()
    return {"status": "success"}

@app.route('/findAbnormal', methods=['POST'])
def findAbnormal():
    """
    Classify last 30 datapoints are normal or abnormal
    """
    input = request.get_json()
    lastCoordinate = DataFrame(getLastCoordinates(30))

    acc_x = lastCoordinate.iloc[:,0:1]
    acc_y = lastCoordinate.iloc[:,1:2]

    #frequency_table_x = acc_x.apply(lambda x: pd.cut(x, bins=[0,0.5,1,1.5,2,2.5,3,3.5,4,4.5,5,5.5,6]).value_counts()).add_prefix('count_')
    #acc_x_mode = (frequency_table_x.idxmax(axis = 0)['count_0'].left + frequency_table_x.idxmax(axis = 0)['count_0'].right)/2
    #acc_x_mean = acc_x.mean()
    #frequency_table_y = acc_y.apply(lambda x: pd.cut(x, bins=[0,0.5,1,1.5,2,2.5,3,3.5,4,4.5,5,5.5,6]).value_counts()).add_prefix('count_')
    #acc_y_mode = (frequency_table_y.idxmax(axis = 0)['count_1'].left + frequency_table_y.idxmax(axis = 0)['count_1'].right)/2
    #acc_y_mean = acc_y.mean()

    # calculate standard deviation
    acc_x_std = acc_x.abs().std()
    acc_y_std = acc_y.abs().std()

    # calculate safety score
    safety_score = 1/acc_x_std[0]/acc_y_std[1]
    segment = ZoneSegment(input['latitude'], input['longitude'], 0, 0, 0, 0)
    # find the closed route segment to find the threshold safety score for current segement
    closed_route = findClosedRouteSegment(segment)

    abnormality="normal"
    if closed_route.safty_sign=='0':
        # if steady behavior is normal
        if float(closed_route.safty_threshold)>safety_score:
            abnormality="abnormal"
        else:
            abnormality="normal"
    else:
        # if steady behavir is abnormal
        if float(closed_route.safty_threshold)>safety_score:
            abnormality="normal"
        else:
            abnormality="abnormal"

    return {
        "status": "success",
        "safety_score": str(safety_score),
        "abnormality": abnormality
    }

def findNextGoal(current_route, direction):
    current_goal = getCurrentGoal()
    time_type = find_time_type()
    print("--------------------")
    if current_goal == 0 and direction is None:
        # if initial goal is not set, start find initial goal
        print("Start finding initial goal")
        goal_id = 0
        path_id = 0
        maxGoalId, maxGoalCount= findMaxGoal(current_route)
        reverse_route = findReverseRoute(current_route)
        reverse_maxGoalId, reverse_maxGoalCount = findMaxGoal(reverse_route)
        print("Found goal " + str(maxGoalId) + " with " + str(maxGoalCount) + " and reverse path goal " +
              str(reverse_maxGoalId) + " with " + str(reverse_maxGoalCount))
        if maxGoalCount > reverse_maxGoalCount:
            goal_id = maxGoalId
            path_id = current_route
        else:
            goal_id = reverse_maxGoalId
            path_id = reverse_route
        print("Initial goal selected: " + str(goal_id) + " with path " + str(path_id))
        return goal_id, path_id
    else:
        # if initial goal already found, then keep predict with existing goal
        next_route = findMaxLink(current_route, current_goal)
        next_goal, max_goal_count = findMaxGoal(next_route)
        print("Next goal selected: " + str(next_goal) + " with path " + str(next_route))
        return next_goal, next_route

def findCurrentRoute(latitude, longitude, direction):
    """
    Find current route by current location and direction
    """
    input = request.get_json()
    currentCoordinate = Track(latitude, longitude, 0)

    mycursor.execute("SELECT * FROM route")
    routeList = mycursor.fetchall()

    minDistance = float("inf")
    pivotCooridnate = Track(0, 0, 0)
    pivotDirection = 0
    # loop in all available routes
    for route in routeList:
        fixedPoint = Track(route[1],route[2], route[4])
        distance = fixedPoint.findDistance(currentCoordinate)
        # find the route with minimum distance to current location
        if distance < minDistance:
            minDistance = distance
            pivotCooridnate = fixedPoint
            pivotDirection = route[3]
    angleDifference = findAcuteAngle(direction, pivotDirection)
    # if route direction also whithin current direction
    if angleDifference <= 90:
        selectedRoute = pivotCooridnate.track_id
    else:
        # if route direction opposite the the current direction
        selectedRoute = findReverseRoute(pivotCooridnate.track_id)
    print('Selected current route: ' + str(selectedRoute))
    return selectedRoute

def addCoordinate(latitude, longitude, track_id,direction, acc_x, acc_y, speed):
    # store current coordinate on the DB
    sql = "INSERT INTO coordinate(latitude, longitude, track_id, direction, acc_x, acc_y, speed) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    val = (latitude, longitude, track_id, direction, acc_x, acc_y, speed)
    mycursor.execute(sql, val)
    mydb.commit()

@app.route('/routes', methods=['POST'])
def getRoutes():
    """
    Get all available route coordinates
    """
    mycursor.execute("SELECT id, latitude, longitude, direction, route_id from route")
    allRoutes = mycursor.fetchall()
    return {
        "route": allRoutes
    }

@app.route('/addSample1', methods=['GET'])
def addSample1():
    """
    add sample1 to test normal behavior of vehicle
    """
    mycursor.execute('''
INSERT INTO coordinate(longitude, latitude, track_id, direction, acc_x, acc_y, speed) VALUES 
(79.90356956,6.795385332,1,145,-0.840313,0.188314,15),
(79.90063565,6.794078088,1,196,0.385518,0.940093,16),
(79.90375321,6.795769889,1,211,-0.122053,0.911363,17),
(79.90047534,6.794204049,1,142,-0.112476,0.346331,18),
(79.90431979,6.795672721,1,210,-0.993542,0.298447,19),
(79.90063834,6.794204005,1,203,-1.141983,0.130853,18),
(79.90385649,6.795868991,1,156,0.165251,0.389427,17),
(79.90401572,6.795586377,1,124,-0.711026,-0.257007,08),
(79.90071853,6.793830481,1,210,-1.103675,-1.200323,09),
(79.90375759,6.795628275,1,198,-0.859467,-0.539523,10),
(79.90111459,6.794170206,1,100,-0.217821,-0.180393,11),
(79.90374492,6.795725227,1,175,0.351999,0.059027,12),
(79.90082146,6.793444936,1,268,-0.639200,-0.668810,13),
(79.90112314,6.793721793,1,200,0.778167,-0.831616,15),
(79.90402592,6.795257162,1,198,0.677611,-0.065471,16),
(79.90072719,6.793758666,1,275,-0.016708,-0.472485,17),
(79.90360241,6.795919077,1,124,-0.481183,-0.319257,18),
(79.90055664,6.793458451,1,237,-0.576951,0.073392,19),
(79.90068307,6.793800539,1,108,0.007234,-0.098990,17),
(79.90436117,6.795507075,1,149,-0.160360,-0.506004,18),
(79.90065185,6.793671203,1,250,-0.150783,-1.094978,19),
(79.90394259,6.795439888,1,200,0.864358,-0.606561,18),
(79.90348275,6.794274395,1,168,1.869923,-0.855558,17),
(79.88504541,6.793696312,1,135,0.318480,-1.913795,09),
(79.88853442,6.795863399,1,145,0.366364,-1.856334,10),
(79.88567672,6.793877147,1,199,-0.361473,-0.874711,11),
(79.88585945,6.794327234,1,174,-0.615258,-0.467697,18),
(79.88940562,6.795821554,1,214,0.059907,-0.051106,19),
(79.90050538,6.794089048,1,124,0.979280,0.169160,07),
(79.90415383,6.795509664,1,214,0.720706,-0.798097,08)
        ''')
    mydb.commit()
    return {
    "success": "true"
    }

@app.route('/addSample2', methods=['GET'])
def addSample2():
    """
    add data sample2 to test abnormal behavior of driver
    """
    mycursor.execute('''
INSERT INTO coordinate(longitude, latitude, track_id, direction, acc_x, acc_y, speed) VALUES 
(79.90356956,6.795385332,1,145,-0.184302,-5.342292,15),
(79.90063565,6.794078088,1,196,1.941749,-1.071036,16),
(79.90375321,6.795769889,1,211,1.122932,0.274505,17),
(79.90047534,6.794204049,1,142,1.098990,-0.467697,18),
(79.90431979,6.795672721,1,210,-0.845102,-0.625714,19),
(79.90063834,6.794204005,1,203,-1.443652,-1.592972,18),
(79.90385649,6.795868991,1,156,-0.059804,-1.698317,17),
(79.90401572,6.795586377,1,124,2.942526,1.083746,08),
(79.90071853,6.793830481,1,210,2.501992,1.653566,09),
(79.90375759,6.795628275,1,198,0.160463,-0.218700,10),
(79.90111459,6.794170206,1,100,-1.443652,-1.813238,11),
(79.90374492,6.795725227,1,175,-2.841866,-0.898653,12),
(79.90082146,6.793444936,1,268,-2.698214,-0.774155,13),
(79.90112314,6.793721793,1,200,-2.195431,-0.640080,15),
(79.90402592,6.795257162,1,198,0.663245,-0.089413,16),
(79.90072719,6.793758666,1,275,3.574595,-0.376718,17),
(79.90360241,6.795919077,1,124,7.050976,-0.376718,18),
(79.90055664,6.793458451,1,237,1.027164,-6.323915,19),
(79.90068307,6.793800539,1,108,0.433402,-6.050976,17),
(79.90436117,6.795507075,1,149,2.602549,-0.213912,18),
(79.90065185,6.793671203,1,250,-0.438087,-1.099766,19),
(79.90394259,6.795439888,1,200,-3.761239,-1.449320,18),
(79.90348275,6.794274395,1,168,-3.751663,-1.343975,17),
(79.88504541,6.793696312,1,135,0.304115,-0.558677,09),
(79.88853442,6.795863399,1,145,5.394188,2.472383,10),
(79.88567672,6.793877147,1,199,0.213135,6.437180,11),
(79.88585945,6.794327234,1,174,-6.624705,-2.565018,18),
(79.88940562,6.795821554,1,214,-3.239303,-1.664798,19),
(79.90050538,6.794089048,1,124,-0.423722,1.366261,07),
(79.90415383,6.795509664,1,214,-0.069380,-1.363129,08)
        ''')
    mydb.commit()
    return {
    "success": "true"
    }
