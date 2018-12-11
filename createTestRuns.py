#!/
# john.hofmeyer@mbww.com
# 09.12.2016
#
# Description:
# 

import mysql
import mysql.connector
import requests
import fileinput
import os
import sys
import time
import datetime
import json
import statistics
import base64

from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, date

## Global values
# sprintEpoch=57, the first Sprint after the 3 week Sprint in 2017.
# Epoch 07/10/2016 = day 1 of sprint 57
# Epoch and sprint start dates should be updated, if we modify our Sprint schedule.

sprintEpoch=57
cadreonEpoch=date(2017,7,10)
daysInSprint=14

user="vRestAutoAPI"
passWord="cadreon123"

jenkinsUser="john.hofmeyer"
jenkinsAPIToken="7ef40b73178fe27db33af8aec620558e"
jenkinsHost="http://"+jenkinsUser+":"+jenkinsAPIToken+"@jenkins.cadreonint.com"

APIHeaders={'Content-Type': 'application/json'}

db=mysql.connector.connect(user='daily_stats', password='yVgvQM7NU&vJXj6637D9',host='qa-daily-stats.ckvgpujcycok.us-east-1.rds.amazonaws.com',database='coverage',buffered=True)
pythonCursor=db.cursor()

acceptableDeferedRate=12.5

def encode(key, clear):
    enc = []
    for i in range(len(clear)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return base64.urlsafe_b64encode("".join(enc))

def decode(key, enc):
	dec = []
	enc = base64.urlsafe_b64decode(enc)
	for i in range(len(enc)):
		key_c = key[i % len(key)]
		dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
		dec.append(dec_c)
	return "".join(dec)

def determineSprintNumber():
	currentSprint=56
	today=date.today()
	if (today>cadreonEpoch):
		thisMonday=today-timedelta(days=today.weekday()) # not really necessary, since we discard the remainder in the next calculation
		sprintsSinceEpoch=((thisMonday-cadreonEpoch).days)/14
		currentSprint=sprintEpoch+sprintsSinceEpoch
	
	return(currentSprint)


def createMilestone(projectID,milestoneName):
	unixDates=getSprintDaysUnix()
	unixStart=unixDates[0]
	unixEnd=unixDates[1]
	
	milestoneData={'name': milestoneName,'start_on': unixStart,'due_on':unixEnd}
									
	newMilestone=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/add_milestone/'+projectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'),data=json.dumps(milestoneData))

	return newMilestone.json()

	
def getSprintFirstDayUnix():
	sprintNumber=determineSprintNumber()
	sprintDay=determineSprintDay()
	
	sprintFirstDay=datetime.today()-timedelta(days=sprintDay)
	sprintLastDay=sprintFirstDay+timedelta(days=11)
	firstDayUnix=getUnixDate(sprintFirstDay)
	lastDayUnix=getUnixDate(sprintLastDay)

	return(firstDayUnix,lastDayUnix)
	
def getSprintDaysUnix():
	sprintNumber=determineSprintNumber()
	sprintDay=determineSprintDay()
	
	sprintFirstDay=datetime.today()-timedelta(days=sprintDay)
	sprintLastDay=sprintFirstDay+timedelta(days=11)
	firstDayUnix=getUnixDate(sprintFirstDay)
	lastDayUnix=getUnixDate(sprintLastDay)

	return(firstDayUnix,lastDayUnix)
	

def getUnixDate(theDate):
	unixDate=str(int((theDate-datetime(1970, 1, 1)).total_seconds()))
	return(unixDate)
	
def determineSprintDay():
	today=date.today()
	currentSprint=determineSprintNumber()
	
	daysSinceEpoch=(today-cadreonEpoch).days
	sprintStart=(currentSprint-sprintEpoch)*14
	sprintDay=daysSinceEpoch-sprintStart
	
	if (sprintDay>4):
		sprintDay-=2
	if (sprintDay>9):
		sprintDay-=2
		
	return (sprintDay)

def determineReleaseNumber():
	currentSprint=determineSprintNumber()
	releaseNumber=currentSprint/2
	if (currentSprint%2 == 1):
		releaseNumber+=1
	
	return("2."+str(releaseNumber))

def determineSprintLookback(cmdOptions)	:
	for scriptCommand in cmdOptions:
		if ("lookback" in scriptCommand):
			return int(scriptCommand.split("=")[1])
	return 4
	
def firstDaySinceLastRelease():
	firstDayLastRelease=str(date(2017,6,3))
	if (date.today()>cadreonEpoch):
		releaseSprint=determineSprintNumber()
		if (releaseSprint%2 == 0):  ## we want the first day of the odd numbered sprint
			releaseSprint-=1

		firstDayLastRelease=str(cadreonEpoch+timedelta(days=(releaseSprint-sprintEpoch)*14-1))
	return(firstDayLastRelease)

def getTicketsAssignedQA(project):
	currentSprint=determineSprintNumber()
	# Get tickets assigned to QA in this Sprint
	projectFilter='{"jql":"Sprint = '+project+'-'+str(currentSprint)+'and%20status%3DResolved","fields":["id","key","priority","created","summary","status","reporter"]}'
	projectSprint=requests.post("https://projects.mbww.com/rest/api/2/search", data=projectFilter, headers=APIHeaders, auth=jiraAuth())
	projectList=projectSprint.json()
	try:
		print projectList['total']," tickets assigned to QA"
	except:
		print "Problem counting tickets assigned to QA"
		print projectList
		
	return (projectList)

def getAllProjectInfo():
	allProjects=pythonCursor.execute("SELECT * FROM projectmapping;")
	for project in allProjects:
		print project
	
	return(allProjects)

def dictContainsValue(dict,theValue,valueName):
	matchCount=0
	for items in dict:
		if (items[valueName] in theValue):
			return items
		if (items[valueName].find(theValue) > -1):
			return items
	return None

def dictValueCount(dict,theValue,valueName):
	matchCount=0
	for items in dict:
		if (items[valueName] in theValue):
			matchCount+=1
		elif (items[valueName].find(theValue) > -1):
			matchCount+=1
			
	return matchCount

		
	
def getOpenedBugsCount(project):
	releaseDayZero=firstDaySinceLastRelease()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug AND cf[12723] != \\"Production Bug\\" AND created > '+releaseDayZero+' ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())

	bugList=currentBugs.json()
	return(bugList['total'])

def getResolvedBugsNotFromBacklog(project):
	releaseDayZero=firstDaySinceLastRelease()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug AND cf[12723] != \\"Production Bug\\" AND created > '+releaseDayZero+' AND resolved > '+releaseDayZero+' ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())
	bugList=currentBugs.json()
	return(bugList['total'])	

def getBugsInBacklog(project):
	releaseDayZero=firstDaySinceLastRelease()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug and status!=Closed ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())
	bugList=currentBugs.json()
	return(bugList['total'])

def getAllResolvedBugs(project):
	releaseDayZero=firstDaySinceLastRelease()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug AND cf[12723] != \\"Production Bug\\" AND resolved > '+releaseDayZero+' ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())
	bugList=currentBugs.json()
	return(bugList['total'])	

def getRegressionBugsCount(project):
	releaseDayZero=firstDaySinceLastRelease()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug AND cf[12727]= \"Regression Test\" AND created > '+releaseDayZero+' ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())

	bugList=currentBugs.json()
	return(bugList['total'])
	
def getSprintTickets(project):
	currentSprint=determineSprintNumber()
	# Get all of the tickets in the current Sprint
	projectFilter='{"jql":"Sprint = '+project+'-'+str(currentSprint)+'","fields":["id","key","priority","created","summary","status","reporter"]}'
	projectSprint=requests.post("https://projects.mbww.com/rest/api/2/search", data=projectFilter, headers=APIHeaders, auth=jiraAuth())
	projectList=projectSprint.json()
	try:
		print projectList['total']," tickets"
	except:
		print "Problem displaying total tickets"
		print projectList
		#if ("does not exist or you do not have permission to view it" in projectList):
		projectList={'total':0}
		
	return (projectList)

def getSprintStories(project):
	currentSprint=determineSprintNumber()
	# Get all of the tickets in the current Sprint
	projectFilter='{"jql":"Sprint = '+project+'-'+str(currentSprint)+' AND type=Story","fields":["id","key","priority","created","summary","status","reporter"]}'
	projectSprint=requests.post("https://projects.mbww.com/rest/api/2/search", data=projectFilter, headers=APIHeaders, auth=jiraAuth())
	
	try:
		projectList=projectSprint.json()
		if (projectList.has_key('errorMessages')):
			print projectList['errorMessages']
		else:
			try:
				print projectList['total']," Stories"
			except:
				print "Problem displaying total tickets"
				print projectList
				projectList={'total':0}
	except Exception as e:
		print projectSprint.text
		print e
		exit()
		
	return (projectList)

def getStoryFilter(projectID):
	projectInfo=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_project/'+projectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	projInf=projectInfo.json()
	jiraProject=projInf['announcement']
	
	if (jiraProject.find("label=") > -1):
		storyLabel=jiraProject.split("label=")[1].split()[0]

		return(storyLabel)

	return None
	
def getAuthentication(env,user,passWord):
	apiHost="qa-api.cadreon.com"
	if (env=="stage"):
		apiHost="stage-api.cadreon.com"
	if (env=="prod"):
		apiHost="cadreon-api.cadreon.com"
	
	params="grant_type=password&username="+user+"&password="+passWord
	url="https://"+apiHost+"/token?"+params
	headerValues={"Accept": "application/json, text/plain, */*","Origin": "https://qa-app.cadreon.com","Authorization": "Basic V0Y5aGxBY2Y4T1ppSDllY3BJY3hYTXdMNlNZYTp1VzdzZHF0OFRZV0NfVURXVkVxZEQ4c09Zd1Fh","Content-Type": "application/x-www-form-urlencoded"}
	
	login=requests.post(url,headers=headerValues)
	loginBody=login.json()
	authToken=loginBody['access_token']
	return (authToken)

def getNetworkAuth():
	theNumber='43'
	unWord='54mzpbTE'
	theWord=decode("theWord",unWord)
	return theNumber+theWord+theNumber

def jiraAuth():
	return(HTTPBasicAuth('john.hofmeyer@mbww.com',getNetworkAuth()))

def confluenceAuth():
	return(HTTPBasicAuth('john.hofmeyer@mbww.com',getNetworkAuth()))
	
	

	
def main():
	# capture script input options, for future use
	cmdOptions = sys.argv
	#print 'Number of arguments:', len(sys.argv), 'arguments.'
	#print 'Argument List:', str(sys.argv)
	sprintLookback=determineSprintLookback(cmdOptions)
	
	jiraAuth=HTTPBasicAuth('john.hofmeyer@mbww.com',getNetworkAuth())
	

	# Status colors
	green='"color: rgb(0,153,0);"'
	yellow='"color: rgb(255,153,0);"'
	red='"color: rgb(255,0,0);"'
	grey='"color: rgb(240,240,240);"'
	black='"color: rgb(255,255,255);"'
	
	# Connect to coverage database
	#db=mysql.connector.connect(user='admin', password='admin',host='127.0.0.1',database='coverage',buffered=True)
	cursor=db.cursor()
	defectCursor=db.cursor()
	subCursor=db.cursor()
	functTestCursor=db.cursor()
	autoRegres=db.cursor()
	autoCursor=db.cursor()
	componentCursor=db.cursor()
	projectCursor=db.cursor()
	
	# Determine current sprint number and sprint day
	currentSprint=determineSprintNumber()
	previousSprint=currentSprint-1
	nextSprint=currentSprint+1
	
	
	sprintName='Sprint '+str(currentSprint)
	sprintDay=determineSprintDay()
	
	dayOneForFilter=str(firstDaySinceLastRelease())
	

	######################################################################################################
	##
	## Jira Ticket Table
	# Jira status: {"New" : 0.0, "Ready" : 0.0, "In Progress" : 0.0, "Reopened" : 0.0, "In Review" : "grey", "Resolved" : 0.0, "Verified" : 0.0, "Closed" : 0.0}
	jiraHeaderColor={"New" : "grey", "Ready" : "blue", "In Progress" : "green", "Reopened" : "red", "In Review" : "grey", "Resolved" : "green", "Verified" : "grey", "Closed" : "blue"}
	jiraHeaderName={"New" : "New", "Ready" : "Ready", "In Progress" : "In Dev", "Reopened" : "Reopened", "In Review" : "In Review", "Resolved" : "in QA", "Verified" : "QA Verified", "Closed" : "Closed"}
	
	jiraTableHeader='<div><table><colgroup><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody>'

	
	
	
	######################################################################################################
	##
	# define query to capture defect reporting
	project_query=('SELECT jira_project FROM projectmapping WHERE project=%s;')
	
	ci_query=('SELECT ci_path FROM projectmapping WHERE project=%s;')
				
	dailyDefects=("SELECT closed_deferred, deferred_count, created_today, critical, major, medium, minor, new_bugs, resolved, in_progress, in_review, verified, reopened, closed"
				   "FROM defects WHERE jira_project=%s and sprint_number=%s and sprint_day=%s ;")
	
	
	print "Current Sprint",currentSprint
	print "Sprint Day #",sprintDay
	
	unixDates=getSprintFirstDayUnix()
	firstDayUnix=unixDates[0]
	lastDayUnix=unixDates[1]
	#print "Sprint Start, Unix: ",firstDayUnix
	#print "Sprint Stop, Unix: ", lastDayUnix
	
	automationMilestone="Sprint "+str(currentSprint)+" - Automated Regression"
	manualMilestone="Sprint "+str(currentSprint)+" - Manual Regression"
	featureMilestone="Sprint "+str(currentSprint)+" - Feature Scenarios"
	performanceMilestone="Sprint "+str(currentSprint)+" - Performance"
	
	old_automationMilestone="Sprint "+str(currentSprint-1)+" - Automated Regression"
	old_manualMilestone="Sprint "+str(currentSprint-1)+" - Manual Regression"
	old_featureMilestone="Sprint "+str(currentSprint-1)+" - Feature Scenarios"
	old_performanceMilestone="Sprint "+str(currentSprint-1)+" - Performance"
	
	#milestoneList={'automation':automationMilestone,'manual':manualMilestone,'feature':featureMilestone}
	milestoneList={'feature':featureMilestone, 'performance':performanceMilestone}
	milestoneID={'automation':0,'manual':0,'feature':0}
	
	dayOneSinceRelease=datetime.strptime(dayOneForFilter,'%Y-%m-%d')
	dateToday=datetime.strptime(str(date.today()),'%Y-%m-%d')
	dateTomorrow=str(dateToday+timedelta(days=(1))).split()[0]
	firstDayOfSprint=str(dateToday-timedelta(days=(sprintDay))).split()[0]
	
	#exit()
	
	# Get the list of all projects in TestRail
	projects=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_projects&is_completed=0', headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	testRailProjects=projects.json()
	
	projectList=[]
	projectDict={}
	projectName=[]
	
	for (projectInfo) in testRailProjects:
		jiraIdList=[]
		if (projectInfo['announcement'] != None):
			jiraProject=projectInfo['announcement']
			if (jiraProject.find("jira=") > -1):		# some Testrail projects may be associated to multiple Jira projects
				jiraId=jiraProject.split("jira=")[1].split()[0]
				if (jiraId.find(",") > -1):
					
					for jirId in jiraId.split(","):
						jiraIdList.append(jirId)
						
					projectDict[str(projectInfo['id'])]=jiraIdList
					#print str(projectInfo['id']),jiraIdList
				else:
					projectDict[str(projectInfo['id'])]=jiraId
					#print str(projectInfo['id']), jiraId
		
	#print projectDict
	#exit()
	'''
	for project in projectDict:
		print project
	exit()
	'''
	
	# Parse each project to determine if it has a current milestone associated
	for projectID in projectDict.keys():
		
		#projectID = str(project['id'])
		perfID=0
		if (projectID not in ("15","16","17","26","27","29","44","46","24","47")):
		#if (projectID in ('52')):
			## projectDict[projectID] = the Jira ID -or- the List of Jira IDs
			## projectID = the Testrail project ID
			
			milestones=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_milestones/'+projectID+"&is_completed=0", headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			projectMilestones=milestones.json()
			
			for milestone in milestoneList:
				milestoneObject=dictContainsValue(projectMilestones,milestoneList[milestone],'name')
				if (milestoneObject is None):
					milestoneObject=createMilestone(projectID,milestoneList[milestone])
					print "Create milestone: ",milestoneList[milestone]
				
				milestoneID[milestone]=milestoneObject['id']
				if milestone=='performance' : perfID=milestoneObject['id']
				
			# check for old milestone - move untested runs to new milestone
			oldMilestoneObject=dictContainsValue(projectMilestones,old_featureMilestone,'name')
			
			
			untestedList=[]
			if (oldMilestoneObject is not None):
				oldRuns=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_runs/'+projectID+"&milestone_id="+str(oldMilestoneObject['id']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
				oldFeatureRuns=oldRuns.json()
				
				newMilestone={'milestone_id' : milestoneID['feature']}
				
				for oldRun in oldFeatureRuns:
					if not oldRun['is_completed']:
						if oldRun['untested_count'] > 0:
							moveRun=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/update_run/'+str(oldRun['id']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'),data=json.dumps(newMilestone))
							try:
								print "moved test run: ",oldRun['name']
							except: 
								print "moved test run: ",str(oldRun['id'])
						else:
							closeRun=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/close_run/'+str(oldRun['id']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))				
							print "closed test run: ",oldRun['name']
						
				closeMilestone={'is_completed': True}
				closedMilestone=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/update_milestones/'+str(oldMilestoneObject['id']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'),data=json.dumps(closeMilestone))
				print "closed milestone: ",oldMilestoneObject['name']
				
			testRuns=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_runs/'+projectID+"&milestone_id="+str(milestoneID['feature']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			featureRuns=testRuns.json()
			
			for run in featureRuns:
				jiraID=run['name'].split(" ")[0].strip()


			projQuery="SELECT jira_project, project FROM projectmapping WHERE testrail_id='"+str(projectID)+"';"
			subCursor.execute(projQuery, projectID)
			if not (subCursor):
				print "Cannot find in database, testrail ID: ",str(projectID)
				subCursor=[]
				subCursor.append(projectDict[str(projectID)])
				#print subCursor
				#exit()
			
			if (subCursor):

				for (jira_project) in subCursor:
				
					if (jira_project[0] is None) and projectDict.has_key(str(projectID)):
						jira_project[0]=projectDict[str(projectID)]
						projNameQuery="SELECT project_name FROM projectmapping WHERE jira_project='"+projectDict[str(projectID)]+"';"
						projectCursor.execute(projNameQuery, projectDict[str(projectID)])
						jira_project[1]=projectCursor[0]
						
						print jira_project[0],jira_project[1]
						exit()
						
					if (jira_project[0]	is not None):
					
						jirProj=jira_project[0]
						projName=jira_project[1]
						
						print
						print ("#"*len(projName))
						print projName
						print ("#"*len(projName))				

					#projQuery="SELECT jira_project FROM projectmapping WHERE project='"+project['name']+"';"
					#subCursor.execute(projQuery, (project['name']))
					#for (jira_project) in subCursor:
						
						#jirProj=jira_project[0]	
				#if (projectDict[projectID] is not None):
					#print projectDict[projectID]
					#for jirProj in projectDict[projectID]:
						
						####
						#  Sprint status
						###
						sprintStories=getSprintStories(jirProj)
						
						if not(sprintStories.has_key('errorMessages')):
						
							totalStories=sprintStories['total']
							
							labelFilter=getStoryFilter(projectID)
							print "Label Filter: ",labelFilter
							
							for story in sprintStories['issues']:

								runScenario=[]

								## Determine if there are labels to exclude the story
								excludeStory=False
							
								## Determine if the summary contains exclusion keywords
								summary=story['fields']['summary']
								summaryUpper=summary.upper()
								
								if("SPIKE" in summaryUpper) or ("DEPLOYMENT" in summaryUpper) or ("TECH DEBT" in summaryUpper) or ("TECHDEBT" in summaryUpper):
								#if ("SPIKE" or "deployment" in summary.upper()):
									pass
									#print "excluding story: ",story['key']
									#print summary.upper()
								
								else:
									storyID=story['key']
									#print story['self']
									
									storyDetail=requests.get(story['self'], headers=APIHeaders, auth=jiraAuth,timeout=None)
									details=storyDetail.json()
									
									## Check if stories should be filter by label
									if (labelFilter is not None):
										labels=details['fields']['labels']
										if (labelFilter[0] == "!"):	## Exclude Stories with this label
											excludeLabel=labelFilter[1:len(labelFilter)]
											if (excludeLabel in labels):
												excludeStory=True
												print "excluding story: ",details['key']," it contains the label: ",excludeLabel
										else:		## Exclude Stories without this label
											if (labelFilter not in labels):
												excludeStory=True
												print "excluding story: ",details['key']," it does not contain the label: ",labelFilter

									if (excludeStory is not True):
										resolutionDate="none"
										resolutionTime="none"
										if (details['fields'].has_key('resolutiondate')):
											if (details['fields']['resolutiondate'] is not None):
												resolutionDate=details['fields']['resolutiondate'].split("T")[0]
												resolutionTime=details['fields']['resolutiondate'].split("T")[1]
										storyStatus=details['fields']['status']['statusCategory']['name'] 
										storyPoints=details['fields']['customfield_10002']
										storyDue="none"
										if (details['fields'].has_key('duedate')):
											storyDue=details['fields']['duedate']
										
										testRunDescription=storyID
										
										## Check for values in Acceptance Scenario field
										if (details['fields'].has_key('customfield_13847')):
											jiraScenarios=details['fields']['customfield_13847']
											if (jiraScenarios != None):
												acceptanceScenarios=jiraScenarios.split("\n")
												testRunDescription+="\n"
												for scenario in acceptanceScenarios:
													testRunDescription+=scenario
											
										
										storyObject=dictContainsValue(featureRuns,storyID,'name')
										
										
										if (storyObject == None):
											print "MISSED STORY"
											runName=storyID+" "+summary
											storyDetails={'name':runName, 'description': 'Test run for Jira ticket: ['+storyID+'](https://projects.mbww.com/browse/'+storyID+')','milestone_id':milestoneID['feature']}
											storyRun=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/add_run/'+projectID+"&milestone_id="+str(milestoneID['feature']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'),data=json.dumps(storyDetails))
											
											storyObject=storyRun.json()
											print "adding test run: ",runName
										
										storyRunCount=dictValueCount(featureRuns,storyID,'name')
										
										
										while (storyRunCount>2):
											storyObject=dictContainsValue(featureRuns,storyID,'name')
											deleteRun=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/delete_run/'+str(storyObject['id']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
											print "Story Run count: "+str(storyRunCount)+" deleted story run id: ",storyObject['id']
											testRuns=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_runs/'+projectID+"&milestone_id="+str(milestoneID['feature']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
											featureRuns=testRuns.json()
											storyRunCount=dictValueCount(featureRuns,storyID,'name')
										
										storyRun=storyObject['id']
										
										
										print storyRun,
										print storyID,
										try:
											print summary
										except:
											print "summary unable to print"
										print "\tStatus:",storyStatus

		# Create Performance Test Run Here
		if (perfID > 0):
			milestoneRuns=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_runs/'+projectID+"&milestone_id="+str(perfID), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			testRailRuns=milestoneRuns.json()
		
			if (len(testRailRuns) > 0):
				testCases=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_cases/'+projectID+'&type_id=8', headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
				tests=testCases.json()
				testList=[]
				includeAll=False
				if len(testList)>0:
					print testCases
					exit()
					perfDetails={'name':runName, 'description': 'Performance test run for Sprint-'+str(currentSprint),'milestone_id':str(perfID),'include_all':False}
				else:
					perfDetails={'name':runName, 'description': 'Performance test run for Sprint-'+str(currentSprint),'milestone_id':str(perfID),'include_all':True}
				storyRun=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/add_run/'+projectID+"&milestone_id="+str(milestoneID['feature']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'),data=json.dumps(storyDetails))
											

	projectCursor.close()
	componentCursor.close()
	cursor.close()
	subCursor.close()
	functTestCursor.close()
	autoRegres.close()
	autoCursor.close()
	pythonCursor.close()
	db.close()
	

	
if __name__ == '__main__':
    main()