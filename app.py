from flask import Flask, request
import mysql.connector
from models.track import Track
import math
from libs.utils import getCurrentGoal, updateCurrentGoal, findReverseRoute, findMaxGoal, findMaxLink, resetGoalRecord, findAcuteAngle

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="root",
    database="router"
)
mycursor = mydb.cursor()
app = Flask(__name__)


@app.route('/')
def index():
    return 'Server Works!'

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
    currentRoot = findCurrentRoute(input['latitude'], input['longitude'], input['direction'])
    next_goal, next_route = findNextGoal(currentRoot)
    updateCurrentGoal(next_goal)
    return {"status": "success", "next_goal": next_goal, "next_route": next_route}

@app.route('/coordinate', methods=['PUT'])
def addCoordinate():
    """Add geo point into the DB
    Inputs:
                latitude (string): latitude of current location
                longitude (string): longitude of current location

            Returns:
                status: Execution status
    """
    input = request.get_json()
    addCoordinate(input['latitude'], input['longitude'], input['track_id'], input['direction'])
    return {"status": "success"}

@app.route('/resetGoal', methods=['POST'])
def resetGoal():
    resetGoalRecord()
    return {"status": "success"}

def findNextGoal(current_route):
    current_goal = getCurrentGoal()

    if current_goal == 0:
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
    print(current_goal)

def findCurrentRoute(latitude, longitude, direction):
    input = request.get_json()
    currentCoordinate = Track(latitude, longitude, 0)

    mycursor.execute("SELECT * FROM route")
    routeList = mycursor.fetchall()

    minDistance = float("inf")
    pivotCooridnate = Track(0, 0, 0)
    pivotDirection = 0
    for route in routeList:
        fixedPoint = Track(route[1],route[2], route[4])
        distance = fixedPoint.findDistance(currentCoordinate)
        if distance < minDistance:
            minDistance = distance
            pivotCooridnate = fixedPoint
            pivotDirection = route[3]

    angleDifference = findAcuteAngle(direction, pivotDirection)
    if angleDifference <= 90:
        selectedRoute = pivotCooridnate.track_id
    else:
        selectedRoute = findReverseRoute(pivotCooridnate.track_id)
    print('Selected current route: ' + str(selectedRoute))
    return selectedRoute

def addCoordinate(latitude, longitude, track_id,direction):
    sql = "INSERT INTO coordinate(latitude, longitude, track_id, direction) VALUES (%s, %s, %s, %s)"
    val = (latitude, longitude, track_id, direction)
    mycursor.execute(sql, val)
    mydb.commit()

