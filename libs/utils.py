import mysql.connector
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
    mycursor.execute("SELECT goal_id, count FROM link_goal_model where link_id=%s", (current_route,))
    initialGoalList = mycursor.fetchall()
    maxGoalCount = 0
    maxGoalId = 0
    for goals in initialGoalList:
        if maxGoalCount < goals[1]:
            maxGoalCount = goals[1]
            maxGoalId = goals[0]
    return maxGoalId, maxGoalCount

def findMaxLink(current_link, current_goal):
    mycursor.execute("SELECT route_to, count from route_map_model WHERE route_from=%s AND current_goal=%s", (current_link, current_goal))
    link_list = mycursor.fetchall()
    max_link_count = 0
    max_link_id = 0;
    for links in link_list:
        if max_link_count < links[1]:
            max_link_count = links[1]
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
     return 360-phi
 else:
     return phi