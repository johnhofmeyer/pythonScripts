#!/
# john.hofmeyer@mbww.com
# 09.07.2016
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
import codecs
import base64
import feedparser

from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, date
from sys import exit
from codecs import decode

## Global values
# sprintEpoch=57, the first sprint of 2016
# Epoch 07/10/2017 = day 1 of sprint 57
# Epoch and sprint start dates should be updated, if we modify our Sprint schedule.

cmdOptions = sys.argv

sep=chr(47)
fo=None

if ("jenkins" not in cmdOptions) or ("scheduled" not in cmdOptions):
	fileName="C:"+sep+"Users"+sep+"John.Hofmeyer"+sep+"Desktop"+sep+"certificationPage.txt"
	fo=open(fileName,'w')	

sprintEpoch=71
cadreonEpoch=date(2018,1,22)

# Create Global Values
today=date.today()
thisMonday=today-timedelta(days=today.weekday()) # not really necessary, since we discard the remainder in the next calculation
sprintsSinceEpoch=((thisMonday-cadreonEpoch).days)/14
currentSprint=sprintEpoch+sprintsSinceEpoch

dateString=""
if (today.month < 10):dateString="0"
dateString+=str(today.month)+"/"
if (today.day<10):dateString+="0"
dateString+=str(today.day)+"/"+str(today.year)

acceptableDeferedRate=12.5

APIHeaders={'Content-Type': 'application/json'}

green='"color: rgb(0,153,0);"'
yellow='"color: rgb(255,153,0);"'
red='"color: rgb(255,0,0);"'
grey='"color: rgb(240,240,240);"'
black='"color: rgb(255,255,255);"'

jenkinsUser="john.hofmeyer"
# Token created on 2018-12-07T12:55:20.24-08:00
jenkinsAPIToken="112a9c96ffb275f8e24c79ce50dec5a223"
#jenkinsHost="http://"+jenkinsUser+":"+jenkinsAPIToken+"@jenkins.cadreonint.com"
jenkinsHost="https://"+jenkinsUser+":"+jenkinsAPIToken+"@jenkins.cadreonint.com"

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

def getCommandValue(keyterm):
	for argVal in sys.argv:
		if (argVal.find(keyterm) > -1):	
			return argVal.split("=")[1]

			
	return (False)
	
def jiraAuth():
	return(HTTPBasicAuth('john.hofmeyer@mbww.com',getNetworkAuth()))
	
def getNetworkAuth():
	theNumber='43'
	unWord='54mzpbTE'
	theWord=decode("theWord",unWord)
	return theNumber+theWord+theNumber
	

def getConfluencePage(pageTitle):
	confluencePage=requests.get("https://wiki.mbww.com/rest/api/content?title="+pageTitle+"&expand=body.view,version,extensions.ancestors", headers={'Content-Type': 'application/json'}, auth=jiraAuth())	
	if (confluencePage.status_code > 299):
		print "Cannot Find: "+pageTitle
		exit()
	return(confluencePage.json())

def getJiraProjectDefectCounts(jiraFilter):
	bugCount=0

	requestFilter='{"jql":'+jiraFilter+',"fields":["id","key","priority","created","summary","status","Bug type"]}'
	bugList=requests.post("https://projects.mbww.com/rest/api/2/search", data=requestFilter, headers=APIHeaders, auth=jiraAuth())
	if bugList.json().has_key('errorMessages'):
		print bugList.text
	else:
		bugCount=len(bugList.json()['issues'])
		if ("summary" in jiraFilter):
			return(bugList.json()['issues'])

	return(bugCount)
	

def updateConfluencePage(pageTitle, pageContent):

	confluencePage=getConfluencePage(pageTitle)

	contentPath=confluencePage['results'][0]['version']['_expandable']['content']
	pageVersion=confluencePage['results'][0]['version']['number']+1
	legacyContent=confluencePage['results'][0]['body']['view']['value']
	
	#logAndPrint(fo, legacyContent)
	#exit()
	
	confluencePutBody = json.dumps({u"version": {u"number": pageVersion},u"title": pageTitle,u"type": u"page",u"body": {u"storage": {u"value": pageContent,u"representation": u"storage"}}})
	confluenceUpdate=requests.put("https://wiki.mbww.com"+contentPath,data=confluencePutBody, headers={'Content-Type': 'application/json'}, auth=jiraAuth())
	
	# A bunch of error handling
	if (confluenceUpdate.status_code > 200):

		logAndPrint(fo,"FAILURE IN upddateConfluencePage")
		logAndPrint(fo,"Failed to update content")
		logAndPrint(fo,"Error code: "+str(confluenceUpdate.status_code))
		print confluenceUpdate.text
		if confluenceUpdate.json().has_key('message'):
			msg=confluenceUpdate.json()['message']
			logAndPrint(fo, msg)
			if ("[row,col {unknown-source}]:" in msg):
				failPoint=int(msg.split("[row,col {unknown-source}]:")[1].split(",")[1].split("]")[0])
				startLog=failPoint-125
				endLog=failPoint+125
				if (startLog<0):startLog=0
				if (endLog>len(pageContent)): endLog=len(pageContent)
				logAndPrint(fo, pageContent)
				logAndPrint(fo, "EXCEPTION IN THE FOLLOWING SECTION")
				logAndPrint(fo, pageContent[startLog:endLog])

	
		print "Attempting to update with existing content"

		confluencePutBody = json.dumps({u"version": {u"number": pageVersion},u"title": pageTitle,u"type": u"page",u"body": {u"storage": {u"value": legacyContent,u"representation": u"storage"}}})
		confluenceUpdate=requests.put("https://wiki.mbww.com"+contentPath,data=confluencePutBody, headers={'Content-Type': 'application/json'}, auth=jiraAuth())
		if (confluenceUpdate.status_code > 200):
			# print confluencePutBody
			print confluenceUpdate.raise_for_status()
		else:
			print "Successfully updated with legacy content"
	else:
		logAndPrint(fo, "Successfully updated Certification page: "+pageTitle)
	
	return(confluenceUpdate.status_code)

def getTestResultCount(projectID,milestoneID):
	runs=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_runs/'+str(projectID)+"&milestone_id="+str(milestoneID)+"&is_completed=0", headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	projectRuns=runs.json()
	results={'passed':0,'failed':0,'blocked':0,'untested':0}

	for run in projectRuns:
		if ("CI" not in run['name']):
			results['passed']+=run['passed_count']+run['custom_status1_count']+run['custom_status4_count']+run['custom_status7_count']
			results['blocked']+=run['blocked_count']
			results['failed']+=run['failed_count']
			results['untested']+=run['untested_count']
	
	return(results)
	
def determineSprintNumber():
	today=date.today()
	
	thisMonday=today-timedelta(days=today.weekday()) # not really necessary, since we discard the remainder in the next calculation
	sprintsSinceEpoch=((thisMonday-cadreonEpoch).days)/14
	currentSprint=sprintEpoch+sprintsSinceEpoch
	
	return(currentSprint)

	
def determineSprintDay(today=date.today()):
	#today=date.today()
	currentSprint=determineSprintNumber()
	
	daysSinceEpoch=(today-cadreonEpoch).days
	sprintStart=(currentSprint-sprintEpoch)*14
	sprintDay=daysSinceEpoch-sprintStart
	
	if (sprintDay>4):
		sprintDay-=2
	if (sprintDay>9):
		sprintDay-=2
		
	return (sprintDay)
	
def firstDaySinceLastRelease(sprintNumber=determineSprintNumber()):
	firstDayLastRelease=str(date(2017,6,3))
	if (date.today()>cadreonEpoch):
		releaseSprint=sprintNumber
		if (releaseSprint%2 == 0):  ## we want the first day of the odd numbered sprint
			releaseSprint-=1

		firstDayLastRelease=str(cadreonEpoch+timedelta(days=(releaseSprint-sprintEpoch)*14-1))
	return(firstDayLastRelease)
	
def getUnixDate(theDate):
	unixDate=str(int((theDate-datetime(1970, 1, 1)).total_seconds()))
	return(unixDate)
	
def getSprintDaysUnix():
	sprintNumber=determineSprintNumber()
	sprintDay=determineSprintDay()
	
	sprintFirstDay=datetime.today()-timedelta(days=sprintDay)
	sprintLastDay=sprintFirstDay+timedelta(days=11)
	firstDayUnix=getUnixDate(sprintFirstDay)
	lastDayUnix=getUnixDate(sprintLastDay)

	return(firstDayUnix,lastDayUnix)
	
def getDictionaryValue(dict,dictKey):
	
	## If the key does not exist, provide debugging info
	if not(dict.has_key(dictKey)):
		print dictKey+" NOT FOUND"
		print "Available Keys and Values:"
		for theKey in dict.keys():
			print "Key: "+theKey+"\tValue: "+dict[theKey]
		
		exit()
		
	return(dict[dictKey])

def getProjectSections(testrailProjectID):
	projectSections=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_sections/'+testrailProjectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	sections=projectSections.json()
	return(sections)
	
def addTestrailSection(testrailProjectID, sectionName, parentID):
	newSection={'name':sectionName,'parent_id':parentID}
	newTestSection=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/add_section/'+testrailProjectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'),data=json.dumps(newSection))
	sectionResponse=newTestSection.json()
	sectionID=sectionResponse['id']
	
	return(sectionID)

def getProductionBugMilestone(projectMilestones):
	determineSprintNumber()
	prodBugMilestoneName="Sprint "+str(determineSprintNumber())+" - Production Bugs"
	
	prodBugMilestone=-1
	for currentMilestone in projectMilestones:
		projectID=currentMilestone['project_id']
		if (currentMilestone['name'].find(prodBugMilestoneName) > -1):
			prodBugMilestone=currentMilestone['id']
	if (prodBugMilestone == -1):
		prodBugMilestone=createMilestone(projectID,prodBugMilestoneName)['id']
	
	return(prodBugMilestone)
	
def createMilestone(projectID,milestoneName):
	unixDates=getSprintDaysUnix()
	unixStart=unixDates[0]
	unixEnd=unixDates[1]
	
	milestoneData={'name': milestoneName,'start_on': unixStart,'due_on':unixEnd}
									
	newMilestone=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/add_milestone/'+str(projectID), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'),data=json.dumps(milestoneData))

	return newMilestone.json()


def updateTestRuns(projectID, milestoneID,jiraTickets):

	testRailRuns=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_runs/'+projectID+"&milestone_id="+str(milestoneID), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	testRuns=testRailRuns.json()
	
	for jiraStory in jiraTickets['issues']:
		jiraID=jiraStory['key']
		summary=jiraStory['fields']['summary']
		runExists=False
		for run in testRuns:
			if (jiraID in run['name']): runExists=True
			
		if (runExists == False):
		
			storyDetail=requests.get(jiraStory['self'], headers=APIHeaders, auth=jiraAuth(),timeout=None)
			details=storyDetail.json()
	
			summaryUpper=summary.upper()
			
			runName=jiraID+" "+summary
			storyDetails={'name':runName, 'description': 'Test run for Jira ticket: ['+jiraID+'](https://projects.mbww.com/browse/'+jiraID+')','milestone_id':str(milestoneID)}
			storyRun=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/add_run/'+projectID+"&milestone_id="+str(milestoneID), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'),data=json.dumps(storyDetails))
											
			storyObject=storyRun.json()
			runLink=storyObject['url']

			description=details['fields']['description']+"\n\n(+) *Test Coverage:*\n"+runLink
			descriptionUpdate=json.dumps({"fields": {"description": description}})
			
			updateJira=requests.put("https://projects.mbww.com/rest/api/2/issue/"+jiraID, data=descriptionUpdate, headers=APIHeaders, auth=jiraAuth())

			print "adding test run: ",runName
			
	return()
	
def determineChildSections(projectSections, sectionID):
	childList=[]
	for section in projectSections:
		## do not check top level sections
		if (section['parent_id'] !=None) and isAncestor(sectionID,section['parent_id'],projectSections):
			childList.append({section['id'],section['name']})
	
	return(childList)
	
def getChildSections(testrailProjectID, sectionID):
	projectSections=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_sections/'+testrailProjectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	sections=projectSections.json()
	
	return(determineChildSections(sections, sectionID))
	
def isAncestor(sectionID, sectionCheck, sections):
	
	if (sectionCheck == sectionID):
		return True
	elif (sectionCheck != None):
		for section in sections:
			if (section['id'] == sectionCheck):
				return (isAncestor(sectionID, section['parent_id'], sections) )

	return (False)

def determineSectionByID(projectSections,sectionID):
	for section in projectSections:
		if (section['id'] == sectionID): return (section)
	return(None)
		

def determineSectionPath(projectSections, sectionID):
	## get the section object
	section=determineSectionByID(projectSections,sectionID)
	## determine if the section is top level
	if (section['parent_id'] is None):
		return ({sectionID:section['name']})
	
	## If not parent, append to the list and get previous gen
	return([{sectionID:section['name']},determineSectionPath(projectSections, section['parent_id'])])

def createDuplicatePath(testrailProjectID, projectSections, obsoleteSections, sectionPath):
	# testrailProjectID = needed to create the new section
	# projectSections = dictionary object with all of the sections
	# obsolete sections = a list of all of the obsolete sections
	# sectionPath = the list of paths to duplicate
	print len(sectionPath)
	
	for section in sectionPath:
		print section
		print section.keys()[0]
		sectionName=section.values()[0]
		
	exit()
		#sectionName=determineSectionByID(projectSections,sectionID)['name']

	return()
	
def getObsoleteTestcount(testrailProjectID):
	## Get a list of test cases that are marked obsolete
	## Obsolete test case has a  test type id = 16
	
	## Create a Dictionary of obsolete tests
	obsoleteTests=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_cases/'+testrailProjectID+'&type_id=16', headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	obsolete=obsoleteTests.json()
	obsoleteCount=len(obsolete)
	
	return(obsoleteCount)

def deteremineObsoletSection(projectSections):
	obsoleteSectionID=-1
	# Check the section in project
	for section in projectSections:
		if (section['parent_id'] is None) and ('obsolete' in section['name'].lower()):
			obsoleteSectionID=section['id']
			return({section['id']:section['name']})

	return({-1:'Obsolete'})

def getObsoleteSection(testrailProjectID):
	## Perhaps this should be stored in the results database
	## Since the section ID does not change on a daily basis

	testrailSections=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_sections/'+testrailProjectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	projectSections=testrailSections.json()
	
	# Create the section if it is missing
	obsoleteSection=deteremineObsoletSection(projectSections)
	
	if(obsoleteSection.keys()[0]<0):
		obsoleteSectionID=addTestrailSection(testrailProjectID, 'Obsolete', None)
		obsoleteSection={obsoleteSectionID:'Obsolete'}
	
	return(obsoleteSection)


def getTotalRegressionTestCount(testrailProjectID,obsoleteSection=-1):
	## Check for the obsoleteSection
	if (obsoleteSection<0):
		obsoleteSection=getObsoleteSection(testrailProjectID).keys()[0]
		
	## Total Test Count
	testCases=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_cases/'+testrailProjectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	if (testCases.status_code > 299):
		print "Exception in request test case count"
		print "Testrail Project ID: ",testrailProjectID
		return(-1)
	else:
		totalTestCount=len(testCases.json())
	
	## Obsolete Test Count
	obsoleteCount=getObsoleteTestcount(testrailProjectID)

	## Return the difference of (Total Tests) - (Obsolete Tests)
	return(totalTestCount-obsoleteCount)


def getJiraInformation(jiraID,filter=None):
	sprintNumber=determineSprintNumber()
	if filter is None:
		filter='{"jql":"Sprint='+jiraID+"-"+str(sprintNumber)+'","fields":["id","key","priority","created","summary","status","reporter"]}'
	
	jiraRequest=requests.post("https://projects.mbww.com/rest/api/2/search", data=filter, headers=APIHeaders, auth=jiraAuth())
	jiraInfo=jiraRequest.json()
	
	if jiraInfo.has_key('errorMessages'):
		print jiraInfo
		print jiraID
		print filter
		exit()
	else:
		print jiraInfo['total']
		print jiraInfo['maxResults']
	
	return(jiraInfo)
	
	
def getClosedSprintBugs(jiraProjectName):
	bugCount=0
	if type(jiraProjectName) is list:
		for jiraProject in jiraProjectName:
			bugCount+=getClosedSprintBugsByProject(jiraProject)
	else:
		bugCount=getClosedSprintBugsByProject(jiraProjectName)
	
	if (bugCount == 0): 
		return([])
	return(bugCount)
			
def getClosedSprintBugsByProject(jiraProject):
	sprintNumber=determineSprintNumber()
	defectFilter='{"jql":"Sprint='+jiraProject+"-"+str(sprintNumber)+' AND issuetype=Bug AND cf[12723] != \\"Production Bug\\" AND Status = Closed ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())

	bugList=currentBugs.json()
	if (bugList.has_key('total')):
		return(bugList['total'])	

	return ([])	
		
def getRecentProductionBugs(jiraProjectName):
	bugList={}
	if type(jiraProjectName) is list:
		for jiraProject in jiraProjectName:
			bugList.update(getProductionBugsByProject(jiraProject))
	else:
		bugList=getProductionBugsByProject(jiraProjectName)

	return(bugList)
		
def getProductionBugsByProject(jiraProject):
	bugList={}
	print "Collecting Production Bugs for "+jiraProject
	if (jiraProject != ""):
		defectFilter='{"jql":"project='+jiraProject+' AND issuetype=Bug AND cf[12723] = \\"Production Bug\\" AND created > -3d ","fields":["id","key","priority","created","summary","status","reporter"]}'
		currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())
		#print currentBugs
		bugList=currentBugs.json()
		
	return(bugList)	


def getSprintBugs(jiraProjectName):
	bugList={}
	if type(jiraProjectName) is list:
		for jiraProject in jiraProjectName:
			bugList.update(getSprintBugsByProject(jiraProject))
	else:
		bugList=getSprintBugsByProject(jiraProjectName)
		
	return(bugList)
	
def getSprintBugsByProject(jiraProject):
	bugList={}
	sprintStartOffset=determineSprintDay()
	if (sprintStartOffset>4): sprintStartOffset+=2
	
	if (jiraProject != ""):
		defectFilter='{"jql":"project='+jiraProject+' AND issuetype=Bug AND cf[12723] != \\"Production Bug\\" AND created > -'+str(sprintStartOffset)+'d ","fields":["id","key","priority","created","summary","status","reporter"]}'
		currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())

		bugList=currentBugs.json()
	return(bugList)	

def getAllOpenBugs(jiraProjectName):
	bugList={}
	if type(jiraProjectName) is list:
		for jiraProject in jiraProjectName:
			bugList.update(getAllOpenBugsByProject(jiraProject))
	else:
		bugList=getAllOpenBugsByProject(jiraProjectName)
	
	return(bugList)
		
def getAllOpenBugsByProject(jiraProject):
	bugList={}
	sprintStartOffset=determineSprintDay()
	if (sprintStartOffset>4): sprintStartOffset+=2
	
	if (jiraProject != ""):
		defectFilter='{"jql":"project='+jiraProject+' AND issuetype=Bug AND Status != Closed","fields":["id","key","priority","created","summary","status","reporter"]}'
		currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())

		bugList=currentBugs.json()
	return(bugList)	
	
def determineCIStatus(jobTitle):
	colorCode={'back':'green','broken':'red','stable':'green','aborted':'red'}
	# extract the status value
	status=jobTitle.split("(")[1].split(")")[0]
	# the first word in the status determines pass or failed
	passFail=status.split(" ")[0]
	
	return (colorCode[passFail])
	

def createProjectPage(projectName):
	sprintNumber=determineSprintNumber()
	sprintDay=determineSprintDay()+1
	
	confluenceBody='<p><h2>Sprint '+str(sprintNumber)+' | Sprint Day '+str(sprintDay)+'</h2></p>'
	
	return(confluenceBody)
	
def addProductionBugs(prodBugs):
	bugCount=0
	if(prodBugs.has_key('total')):
		bugCount=prodBugs['total']
	
	# Should list all of the production bugs, here
	return ('<p><h2 id="ProductionBugs">Production Bugs</h2></p><p style="margin-left: 30.0px;">'+str(bugCount)+'</p>')
	
	
	
def addSprintBugs(sprintBugs):
	
	sprintBugStatus={}
	bugStats='<p><h2 id="TestCoverage-SprintBugs">Sprint Bugs</h2></p><p style="margin-left: 30.0px;">'
	#logAndPrint(fo,"### Sprint Bugs ###")
	if (sprintBugs.has_key('total')):
		for bug in sprintBugs['issues']:
			status=bug['fields']['status']['statusCategory']['name']
			if (sprintBugStatus.has_key(status)):
				sprintBugStatus[status]+=1
			else:
				sprintBugStatus[status]=1

		for bugType in sprintBugStatus:
			bugStats+=bugType+':'+str(sprintBugStatus[bugType])+'    '
				
	else:
		bugStats+="No Bugs"
		
	return(bugStats+'</p>')

def updateDefectTable(projectCursor,sprintNumber, sprintDay, project, defectCounts):
	defectStatus={}
	sprintYesterday=int(sprintDay)-1
	#defectStatus={"New":0, "In Progress":0, "In Review":0, "Resolved":0, "Reopened":0, "Verified":0, "Closed":0}
	#print sprintNumber, sprintDay,project,defectCounts
	for key in defectCounts:
		defectStatus.update({key:{"today":defectCounts[key],"yesterday":0}})

	projectCursor.execute("SELECT Count(*) from defects WHERE sprint_number = "+sprintNumber+" and sprint_day = "+sprintDay+" and jira_project = '"+project+"'; ",)
	resultCount=0
	for rowCount in projectCursor:
		resultCount=rowCount[0]
		
	if (resultCount>0): # If the row exists, perform an UPDATE
		projectCursor.execute("UPDATE defects SET newDefects = "+str(defectCounts['New'])+" , inDev = "+str(defectCounts['In Progress'])+" , reopened = "+str(defectCounts['Reopened'])+" , inReview = "+str(defectCounts['In Review'])+" , inQA = "+str(defectCounts['Resolved'])+" , verified = "+str(defectCounts['Verified'])+" , closed = "+str(defectCounts['Closed'])+""
			"WHERE sprint_number = "+str(sprintNumber)+" AND sprint_day = "+str(sprintDay)+" AND project= "+project+"",
			"VALUES (%s)",str(sprintNumber))	
			
	else:	 # if the row does not exist, perform an INSERT
		projectCursor.execute("INSERT into defects "
		"(sprint_number, sprint_day, jira_project, newDefects, inDev, reopened, inReview, inQA, verified, closed) "
		"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",(str(sprintNumber), str(sprintDay), project, defectCounts['New'], defectCounts['In Progress'], defectCounts['Reopened'], defectCounts['In Review'], defectCounts['Resolved'], defectCounts['Verified'], defectCounts['Closed']))

	db.commit()
	
	return defectStatus

def getJiraTicket(jiraID):
	if (validJiraId(jiraID)):
		storyFilter='{"jql":"Id = '+jiraID+'","fields":["id","key","priority","created","summary","status","reporter"]}'
		storyQuery=requests.post("https://projects.mbww.com/rest/api/2/search", data=storyFilter, headers=APIHeaders, auth=jiraAuth())
		try:
			jiraStory=storyQuery.json()
		except:
			print "failed to get story id",jiraID
			print storyQuery
			exit()
	
		return(jiraStory)
	
	return({})
		
def validJiraId(jiraId):
	for letter in jiraId:
		isInteger=letter.isnumeric()
	return(isInteger)	
		

def getChangeLog(jiraID):
	changeLog={}
	jiraLog=requests.get("https://projects.mbww.com/rest/api/2/"+jiraID+"", headers=APIHeaders, auth=jiraAuth(),timeout=None)
	try:
		changeLog=jiraLog.json()
	except:
		print "Failed to get Jira Log"
		print jiraLog
		
	#print changeLog
	#exit()
	
	return(changeLog)
	
	
def getJiraDetails(jiraID):
	jiraTicket=getJiraTicket(jiraID)
	
	if (jiraTicket.has_key('errorMessages')):
		errMsg=""
		for errs in jiraTicket['errorMessages']:
			errMsg+="\n"+errs
		print errMsg
		
		return("error",errMsg,"")
	
	try:
		jiraIssue=jiraTicket['issues'][0]
	except:
		print "Jira ticket failure"
		print jiraID
		print jiraTicket
		return("error","error","error","error")
	
	storyDetail=requests.get(jiraIssue['self'], headers=APIHeaders, auth=jiraAuth(),timeout=None)
	details=storyDetail.json()
	
	##
	## Check if the Jira ticket is a Bug
	##
	if (details['fields']['issuetype']['name'] == "Bug"):
		storyID=None
		if (details['fields'].has_key('issuelinks')):
			if (details['fields']['issuelinks'] != []):
				defectDetail=requests.get(details['fields']['issuelinks'][0]['self'], headers=APIHeaders, auth=jiraAuth(),timeout=None)
				defectDetails=defectDetail.json()
				
				if defectDetails.has_key('inwardIssue'):
					if (defectDetails['inwardIssue']['fields']['issuetype']['name'] == 'Story'):
						return (defectDetails['inwardIssue']['key'])
				elif defectDetails.has_key('outwardIssue'):
					if (defectDetails['outwardIssue']['fields']['issuetype']['name'] == 'Story'):
						return (defectDetails['outwardIssue']['key'])
						
		return(storyID)
		
	else:
		bugCount=getStoryBugCount(details)

	#print "bug Count: ",bugCount
	#if (bugCount > 0): exit()
	dueDate=""
	if (details['fields'].has_key('duedate')):
		storyDue=str(details['fields']['duedate'])
	
	resolvedDate=""
	if (details['fields'].has_key('resolutiondate')):
		if (details['fields']['resolutiondate'] is not None):
			resolvedDate=details['fields']['resolutiondate']

	storyStatus=details['fields']['status']['statusCategory']['name'] 
	storyPoints=str(details['fields']['customfield_10002'])

	return(storyStatus,storyPoints,storyDue,bugCount,resolvedDate)

def getStoryBugCount(storyDetail):
	bugCount=0
	if (storyDetail['fields'].has_key('issuelinks')):
		
		for issue in storyDetail['fields']['issuelinks']:
			if issue.has_key('inwardIssue'):
				if (issue['inwardIssue']['fields']['issuetype']['name'] == 'Bug'):
					bugCount+=1
					
			elif issue.has_key('outwardIssue'):
				if (issue['outwardIssue']['fields']['issuetype']['name'] == 'Bug'):
					bugCount+=1

	return (bugCount)

def getParentStory(defectDetail):
	print defectDetail
	
	for issue in defectDetail:
		if issue.has_key('inwardIssue'):
			if (issue['inwardIssue']['fields']['issuetype']['name'] == 'Story'):
				return (issue['inwardIssue']['key'])
		elif issue.has_key('outwardIssue'):
			if (issue['outwardIssue']['fields']['issuetype']['name'] == 'Story'):
				return (issue['outwardIssue']['key'])
				
	return (None)
	
def isOldDate(theWord):
	fullDate=theWord.split("/")
	
	if len(fullDate)==2:

		tMonth=int(fullDate[0])-int(today.month)
		tDay=int(fullDate[1])-int(today.day)
		tYear=int(fullDate[2])-int(today.year)
		
		if (tMonth+tDay+tYear == 0): return False

	return True

def getTicketTableHeader(type=None):
	tableHead='<div><table>'
	if (type == "region"):
		tableHead+='<colgroup><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr>'
		tableHead+='<th class="confluenceTh">Project</th>'
	else:
		tableHead+='<colgroup><col/><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr>'
	tableHead+='<th class="confluenceTh">Jira Ticket</th>'
	tableHead+='<th class="confluenceTh">Points</th>'
	tableHead+='<th class="confluenceTh">Jira Status</th>'
	tableHead+='<th class="confluenceTh">Test Status</th>'
	tableHead+='<th class="confluenceTh">Passed</th>'
	tableHead+='<th class="confluenceTh">Failed</th>'
	tableHead+='<th class="confluenceTh">Blocked</th>'
	tableHead+='<th class="confluenceTh">Untested</th>'
	tableHead+='<th class="confluenceTh">Bugs</th></tr>'
	
	return(tableHead)

def getRegressionTableHeader(type=None):
	tableHead='<p><h2 id="TestCoverage-AutomatedRegression">Automated Regression</h2></p>'
	tableHead+='<div><table>'
	if (type == "region"):
		tableHead+='<colgroup><col/><col/><col/><col/></colgroup><tbody><tr>'
		tableHead+='<th class="confluenceTh">Project</th>'
	else:
		tableHead+='<colgroup><col/><col/><col/><col/></colgroup><tbody><tr>'
	
	tableHead+='<th class="confluenceTh">Passed</th>'
	tableHead+='<th class="confluenceTh">Failed</th>'
	tableHead+='<th class="confluenceTh">Blocked</th>'
	tableHead+='<th class="confluenceTh">Untested</th>'
	tableHead+='<th class="confluenceTh">Total Test Count</th></tr>'
	
	return(tableHead)

def getCITableHeader(type=None):
	tableHead='<p><h2 id="TestCoverage-CI">Continuous Integration</h2></p>'
	tableHead+='<div><table>'
	if (type == "region"):
		tableHead+='<colgroup><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr>'
		tableHead+='<th class="confluenceTh">Project</th>'
	else:
		tableHead+='<colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr>'
	
	tableHead+='<th class="confluenceTh">Component</th>'
	tableHead+='<th class="confluenceTh">Current Build</th>'
	tableHead+='<th class="confluenceTh">Status Since Build</th>'
	tableHead+='<th class="confluenceTh">Pass</th>'
	tableHead+='<th class="confluenceTh">Fail</th></tr>'
	
	return(tableHead)

def getTrendTableHeader(type=None):
	tableHead='<p><h2 id="TestTrend">Test Trend</h2></p>'
	tableHead+='<div><table>'
	if (type == "region"):
		tableHead+='<colgroup><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr>'
		tableHead+='<th class="confluenceTh">Project</th>'
	else:
		tableHead+='<colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr>'
	
	tableHead+='<th class="confluenceTh">Day</th>'
	tableHead+='<th class="confluenceTh">Passed</th>'
	tableHead+='<th class="confluenceTh">Failed</th>'
	tableHead+='<th class="confluenceTh">Blocked</th>'
	tableHead+='<th class="confluenceTh">Untested</th></tr>'
	
	return(tableHead)

def getTwelveHourTime(theTime):
	# 17:05:58.000+0000 example time
	meridiem=" am"
	theHour=int(theTime.split(":")[0])
	if (theHour>11):
		meridiem=" pm" 							# change to PM, if 12 or later
		if (theHour>12):theHour=theHour-12	   	# subtract 12 from the hour if it exceeds 12
	
	theMinute=int(theTime.split(":")[1])
	theSecond=int(theTime.split(":")[2].split(".")[0])  ## only want seconds, not ms
	
	twelveHourTime=str(theHour)+":"+str(theMinute)+meridiem ## decided not to pass along seconds
	
	return(twelveHourTime)

def addValueToDict(dict,dictKey,theValue):
		if dict.has_key(dictKey):
			dict[dictKey]=dict[dictKey]+theValue
		else:
			dict[dictKey]=theValue
		
		return(dict)
	
def excludeRun(runName):
	notDates=["sprint","automated","manual","regression","functional","ui","api","test","tests","run"]
	containsOldDate=isOldDate(runName.split()[-1])

	#if (isOldDate(runName.split()[-1])): containsOldDate=True

	return containsOldDate
	
def parseJiraBugs(issueList):
	jiraBugCount=0
	bugList="No Bugs"
	try:
		for issue in issueList:
			issueName=issue['inwardIssue']['fields']['issuetype']['name']
			if (issueName=="Bug"): 
				bugSummary=issue['inwardIssue']['fields']['summary']
				jiraBugCount+=1
				if (bugList=="No Bugs"):
					bugList='\t'+str(issue['inwardIssue']['key']+": "+bugSummary)
				else:
					bugList+=chr(13)+'\t'+str(issue['inwardIssue']['key']+": "+bugSummary)
		
		if (jiraBugCount==1):
			return("1 associated bug"+chr(13)+bugList+chr(13))
		if (jiraBugCount>1):
			return(str(jiraBugCount)+" associated bugs"+chr(13)+bugList+chr(13))
	except:
		pass
		#return(chr(13)+bugList+chr(13))
		
	return(bugList)

## Determine if a Jira project is in the testrail project
def getJiraIDFromTestrail(projAnnouncement):
	if (projAnnouncement is not None):
		if ("jira=" in projAnnouncement):

			jiraId=projAnnouncement.split("jira=")[1].split()[0]
			if (jiraId.find(",") > -1):
				
				jiraIdList=[]
				for jirId in jiraId.split(","):
					jiraIdList.append(jirId)
						
				return(jiraIdList)
			else:
				jiraIdList=[jiraId]
				return(jiraIdList)

	return(None)
	
## Capture component list from testrail project
def getComponents(projAnnouncement):
	if (projAnnouncement is not None):
		if ("components=" in projAnnouncement):
			componentDict=projAnnouncement.split("components=")[1].split()[0]
			try:
				return(json.loads(componentDict))
			except Exception as e:
				print "*****************************"
				print "ERROR PARSING COMPONENTS JSON"
				print e
				print componentDict
				print "*****************************"
			
	return(None)

def getLatestBuildPromotionLink(jenkinsJob):
	promotionLink=None
	lastSuccessBuild=".?."
	buildLink="n/a"
	
	# jenkinsHost is a global value
	jenkinsQABuildPromotion=jenkinsJob.replace("jenkins.cadreonint.com",jenkinsHost)
	componentQAPromotion=requests.get(jenkinsQABuildPromotion)
	
	if (componentQAPromotion.status_code <300):
		try:
			componentInfo=componentQAPromotion.json()
		except Exception as e: 
			print jenkinsQABuildPromotion
			print componentQAPromotion.json()
			print "FAIL"
			print e
			
		lastSuccessBuild=componentInfo['id']
		buildLink=componentInfo['url']
	
	print jenkinsQABuildPromotion
	print componentQAPromotion
	exit()
	
	promotionLink=jenkinsJob+lastSuccessBuild+"/promotion/"
	
	return(promotionLink)
	
def logAndPrint(theLog,message):
	try:
		if (theLog != None):
			theLog.writelines(message+chr(13))
		
		printOut=message.split(chr(13))
		for lineOut in printOut:
			print lineOut+'\r\n'
	except:
		print "**** FAILURE in LOGGING ****"
	
	return

def main():
	# capture script input options, for future use
	cmdOptions = sys.argv
	
	sep=chr(47)
	fo=None
	
	if ("jenkins" not in cmdOptions) or ("scheduled" not in cmdOptions):
		fileName="C:"+sep+"Users"+sep+"John.Hofmeyer"+sep+"Desktop"+sep+"certificationPage.txt"
		fo=open(fileName,'w')	
	

	jiraAuth=HTTPBasicAuth('john.hofmeyer@mbww.com',getNetworkAuth())
	updateResults=True
	
	# Determine current sprint number, current Sprint day, and first day of Sprint 
	currentSprint=determineSprintNumber()
	sprintName="Sprint "+str(currentSprint)
	sprintDay=determineSprintDay()
	
	# Determine the first day of the sprint
	sprintFirstDay=str(cadreonEpoch+timedelta(days=(currentSprint-sprintEpoch)*14-1)) # Technically, this is the Sunday before the Sprint begins
	firstDayUnix=datetime.today()-timedelta(days=sprintDay)
	if (sprintDay>5):
		firstDayUnix=(datetime.today()-timedelta(days=sprintDay+2))
	firstDayUnix=str(int((firstDayUnix-datetime(1970, 1, 1)).total_seconds()))
	
	# Determine release date for Staging and Production
	ProdReleaseSunday=firstDaySinceLastRelease(currentSprint+1) 

	releaseYear=ProdReleaseSunday.split("-")[0]
	releaseMonth=ProdReleaseSunday.split("-")[1]
	releaseDay=ProdReleaseSunday.split("-")[2]

	ProdReleaseDate=date(int(releaseYear),int(releaseMonth),int(releaseDay))+timedelta(days=1)
	StageReleaseDate=date(int(releaseYear),int(releaseMonth),int(releaseDay))-timedelta(days=2)

	#print StageReleaseDate.strftime("%A, %B %d"), ProdReleaseDate.strftime("%A, %B %d")
	#exit()

	
	msg= "Current Sprint: "+str(currentSprint)
	logAndPrint(fo,msg)
	msg= "Sprint Day #"+str(sprintDay+1)
	logAndPrint(fo,msg)

	dateToday=date(datetime.today().year,datetime.today().month,datetime.today().day)
	if (sprintDay == 0) or (sprintDay==5):
		dateYesterday=dateToday-timedelta(days=3)
	else:
		dateYesterday=dateToday-timedelta(days=1)
	
	######################################################################################################
	##
	## Certification Table
	
	certTableHeader='<p></p><p></p>' #<p>Certification Metrics</p>'
	certTableHeader+='<div><table>'
	certTableHeader+='<colgroup><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody>'
	certTableHeader+='<tr><th class="confluenceTh">Test Areas</th>'
	certTableHeader+='<th class="confluenceTh"><p>(A) Total TC</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(B) TC attempted</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(C) % TC Attempted</p><p><span style="color: rgb(51,102,255);">(B/A)* 100</span></p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(D) TC Passed</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(E) % TC Passed</p><p><span style="color: rgb(51,102,255);">(D/A)* 100</span></p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(F) Open Bugs</p><p>w/ High Priority</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(G) Bugs found</p><p>in this cycle</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(H) Bugs resolved excluding bugs from backlog</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(I) Bugs resolved including bugs from backlog</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(J) Bugs in backlog</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(K) % Bugs Deferred</p><p>excluding bugs from backlog</p><span style="color: rgb(51,102,255);">((G - H)/G) * 100</span></th>'
	certTableHeader+='<th class="confluenceTh"><p>(L) % Bugs Deferred</p><p>including bugs from backlog</p><span style="color: rgb(51,102,255);">((G - I)/G) * 100</span></th>'
	certTableHeader+='<th class="confluenceTh"><p>Meet Criteria?</p><p>Threshold for this release is '+str(acceptableDeferedRate)+'%</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>Staging Acceptance Tests Pass</p><p><span style="color: rgb(51,153,102);">pass</span>: yes</p><p><span style="color: rgb(255,0,0);">fail</span>: list JIRA ticket(s)</p></th></tr>'
	
	confluenceBody='<p><h2>Release Sprints '+str(currentSprint-1)+' and '+str(currentSprint)+'</h2></p>'
	
	certificationPage='<h2 id="ExitCriteriaRequirements">Exit Criteria Requirements</h2>'
	certificationPage+='<p>The following exit criteria must be complete before a release is considered READY for production</p>'
	certificationPage+='<ul class="ul1"><li>100% of test cases attempted</li>'
	certificationPage+='<li>90% of test cases passed</li><li>No open high severity defects exist</li>'
	certificationPage+='<li>Bug deferral rate less than '+str(acceptableDeferedRate)+'%</li></ul>'
	
	certificationPage+='<h2 id="ReleaseDates">Deployment Dates</h2>'
	certificationPage+='<p>Staging Deployment: '+StageReleaseDate.strftime("%A, %B %d")+', 4:00 pm Pacific</p>'
	certificationPage+='<p>Production Deployment: '+ProdReleaseDate.strftime("%A, %B %d")+', 5:00 pm Pacific</p>'
	
	certification=certificationPage+certTableHeader #+'<p> </p><hr/><p> </p>'
	
	######################################################################################################
	##
	## DevOps Table
	
	if (currentSprint % 2 == 0):
		includedSprints="<p>Sprint "+str(currentSprint)+"</p>\n<p>Sprint "+str(currentSprint-1)+"</p>"
	else:
		includedSprints="Sprint "+str(currentSprint)+"</p>\n<p>Sprint "+str(currentSprint+1)+"</p>"
	
	devOpsTable='<div><table><colgroup><col/><col/></colgroup><tbody>'				# Two columns
	devOpsTable+='<tr><td>Initiated through ticket</td><td>DEPLOY-{ }</td></tr>' 	# Row #1
	devOpsTable+='<tr><td>Included Sprints</td><td>'+includedSprints+'</td></tr>'	# Row #2
	devOpsTable+='<tr><td>Stage Promotion</td><td> </td></tr>'						# Row #3
	devOpsTable+='<tr><td>Production Promotion</td><td> </td></tr>'					# Row #4
	devOpsTable+='<tr><td>Team</td><td> </td></tr>'									# Row #5
	devOpsTable+='</tbody></table></div>'											# Row #6
	
	
	######################################################################################################
	##
	## Promotion Table
	
	promoTableHeader='<div class="table-wrap"><table class="relative-table wrapped confluenceTable" style="width: 100.0%;">'
	# Define Columns and start table body
	#promoTableHeader+='<colgroup><col style="width: 8.38881%;"/><col style="width: 7.92277%;"/><col style="width: 28.8948%;"/><col style="width: 4.72703%;"/><col style="width: 4.72703%;"/><col style="width: 5.1265%;"/><col style="width: 6.59121%;"/><col style="width: 6.59121%;"/><col style="width: 6.52463%;"/><col style="width: 7.32357%;"/><col style="width: 6.85752%;"/><col style="width: 6.3249%;"/></colgroup><tbody>'
	promoTableHeader+='<colgroup><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody>'
	
	# Column Headers
	promoTableHeader+='<tr><td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h2>Component</h2></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h4><p>Quality Lead</p></h4></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h3>Certified Build and Jenkins Promotion Link</h3></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><strong>Should Deploy To Stage</strong></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><strong>Should Deploy To Prod</strong></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><strong>Should Deploy To Support</strong></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h4>Pre and Post Deployment Steps</h4></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h3>Stage</h3><p>Deployment Completed?</p><p>(To Be Filled ByDevOps)</p></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h3>Prod</h3><p>Deployment Completed?</p><p>(To Be Filled By DevOps)</p></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h3>Support</h3><p>Deployment Completed?</p><p>(To Be Filled By DevOps)</p></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h4>Production Acceptance Test Confirmation Link</h4></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" data-highlight-colour="grey"><h3>Comment</h3></td></tr>'
	
	promoTable=promoTableHeader
	promoTableClose='</tbody></table></div>'

	################
	##
	##  Define dictionaries for test cases
	
	dueDate=""
				
	baseFilter='https://projects.mbww.com/issues/?jql='
	
	resultText={'1':'passed','2':'blocked','3':'untested','4':'Retest','5':'Failed','6':'In Progress','7':'Untested-Late','8':'Untested n/a','10':'Passed-Support','11':'Passed-Stage','12':'Passed-Production'}

	totalAutomated=0
	totalTestCount=0
	projectList=[]
	
	regionInclude=getCommandValue("region")
	skipProjects=getCommandValue("skip")
	
	sprintLookback=int(getCommandValue("lookback"))
	if not (sprintLookback): sprintLookback=2
	startSprint=currentSprint-(sprintLookback-1)
	firstDayOfCycle=str(cadreonEpoch+timedelta(days=(startSprint-sprintEpoch)*14-1))
	
	projects=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_projects&is_completed=0', headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	testRailProjects=projects.json()
	
	bugDateFilter=str(firstDaySinceLastRelease())
	
	certTable='<p> </p><hr/><p> </p>'+certTableHeader
	
	for project in testRailProjects:
		jiraProject=getJiraIDFromTestrail(project['announcement'])
				
		#if jiraProject is not None:
			#if "CMTA" not in jiraProject: jiraProject=None
			
		if jiraProject is not None:
		
			###################################################
			##
			##	Deploy tickets
			##
			###################################################
			
			for jp in jiraProject:
			
				## Get the Deploy ticket
				deployTicket="unknown"
				deployLink=baseFilter+jp+'-'+str(currentSprint)+' AND summary ~%22DEPLOY%22'
				jiraFilter='"sprint='+jp+'-'+str(currentSprint)+' AND Status !=Closed AND summary ~ \\"DEPLOY\\""'

				requestFilter='{"jql":'+jiraFilter+'}'
				ticketList=getJiraProjectDefectCounts(jiraFilter)
				if (ticketList != 0):
					promoRow='<tr><td class="highlight-grey confluenceTd" colspan="2" data-highlight-colour="grey">'
					for deployTicket in ticketList:
						promoRow+='<h3 id="CertificationPage-'+jp+'Trackerkey-'+deployTicket['key']+'">'+jp+'</h3></td>'
						## Add link to build promotion
						## promoRow+='<div class="content-wrapper">'
						promoRow+='<td class="highlight-grey confluenceTd" colspan="10" data-highlight-colour="grey">'
						promoRow+='Deployment Ticket: <a class="external-link" href="https://projects.mbww.com/browse/'+deployTicket['key']+'" rel="nofollow" target="_blank" data-ext-link-init="true">'+deployTicket['key']+'</a>'
						## promoRow+='</td></div></tr>'
						promoRow+='</td></tr>'
				else:
					
					promoRow='<tr><td class="highlight-grey confluenceTd" colspan="2" data-highlight-colour="grey">'
					promoRow+='<h3 id="CertificationPage-'+jp+'Trackerkey-unkown">'+project['name']+'</h3></td>'
					promoRow+='<td class="highlight-grey confluenceTd" colspan="10" data-highlight-colour="grey">'
					promoRow+='Deployment Ticket: <a class="external-link" href="'+baseFilter+deployLink+'" rel="nofollow">unknown</a>'
					promoRow+='</td></tr>'
				
				promoTable+=promoRow
				
			###################################################
			##		
			##	Components
			##
			###################################################
			
				components=getComponents(project['announcement'])
				if components != None:
					print "Gathering Components ",
					try:
						for component in components:
							promoPath=components[component].replace("https://jenkins.cadreonint.com",jenkinsHost)+"promotion/process/deploy-qa/rssAll"	
							buildList=feedparser.parse(promoPath)

							buildNumber=None
							for build in buildList['entries']:
								if (buildNumber == None):
									if ("stable") in build['title']:
										print ".",
										##print build['links'][0]['href'].split("promotion/")[0]
										buildNumber=build['title'].split("#")[1].split()[0]
										buildLink=build['links'][0]['href'].split("promotion/")[0]+'promotion'
										
										promoRow='<tr><td>'+component+'</td>'
										promoRow+='<td></td><td><a class="external-link" href="'+buildLink+'" rel="nofollow">Build '+buildNumber+'</a></td>'
										promoRow+='<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>'
										promoTable+=promoRow
						print
					except Exception as e:
						print components
						print e
						exit()
				
				else:
					promoRow='<tr><td>'+project['name']+'</td>'
					promoRow+='<td></td><td>'+jp+' Build</td>'
					promoRow+='<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>'
					promoTable+=promoRow
		
			sprintList='sprint in ('
			projectList='project in ('
			
			for jp in jiraProject:
				projectList+=jp
				for sprintBack in range(sprintLookback):
					sprintList+=jp+'-'+str(currentSprint-sprintBack)+', '
				
				if len(jiraProject) > 1: 
					projectList+=', '
				
			sprintList+=')'
			projectList+=')'
			
			if sprintList.endswith(', )'):
				sprintList=sprintList[0:len(sprintList)-3]+')'
				
			if projectList.endswith(', )'):
				projectList=projectList[0:len(projectList)-3]+')'
			
			print project['name']

			
			# Column F - open Bugs with High Priority
			highPriorityBugs=sprintList+' AND type=Bug AND status != Closed AND priority in (Critical, High) AND cf[12723] !=%22Production%20Bug%22'
			jiraFilter='"'+sprintList+' AND type=Bug AND status != Closed AND priority in (Critical, High) AND cf[12723] !=\\"Production Bug\\""'
			highPriorityBugsCount=getJiraProjectDefectCounts(jiraFilter)
			
			# Column G - bugs found in this cycle
			foundInCycle=projectList+' AND type=Bug AND created%20%3E%20'+firstDayOfCycle+' AND cf[12723] !=%22Production%20Bug%22'
			jiraFilter='"'+projectList+' AND type=Bug AND created>'+firstDayOfCycle+' AND cf[12723] !=\\"Production Bug\\""'
			foundInCycleCount=getJiraProjectDefectCounts(jiraFilter)
			
			# Column H - bugs resolved, not from backlog
			bugsResolved=sprintList+' AND type=Bug AND created%20%3E%20'+bugDateFilter+' AND status=Closed AND cf[12723] !=%22Production%20Bug%22'
			jiraFilter='"'+sprintList+' AND type=Bug AND created>'+bugDateFilter+' AND status=Closed AND cf[12723] !=\\"Production Bug\\""'
			bugsResolvedCount=getJiraProjectDefectCounts(jiraFilter)
			
			# Column I - bugs resolved, including backlog
			bugsFromBacklog=sprintList+' AND type=Bug AND status=Closed AND cf[12723] !=%22Production%20Bug%22'
			jiraFilter='"'+sprintList+' AND type=Bug AND status=Closed AND cf[12723] !=\\"Production Bug\\""'
			bugsFromBacklogCount=getJiraProjectDefectCounts(jiraFilter)		
			
			# Column J - bugs in backlog
			totalBacklog=projectList+' AND type=Bug AND status !=Closed AND cf[12723] !=%22Production%20Bug%22'
			jiraFilter='"'+projectList+' AND type=Bug AND status !=Closed AND cf[12723] !=\\"Production Bug\\""'
			totalBacklogCount=getJiraProjectDefectCounts(jiraFilter)		
			
			# Column K - percent deferred
			defPercent='0.00%'
			deferedCount=foundInCycleCount-bugsResolvedCount
			if deferedCount > 0:
				defPercent='{:.2%}'.format(float(deferedCount)/float(foundInCycleCount))
				
			# Column L - deferred from backlog
			defBacklogPercent='0.00%'
			deferedCount=foundInCycleCount-bugsFromBacklogCount
			if deferedCount > 0:
				defBacklogPercent='{:.2%}'.format(float(deferedCount)/float(foundInCycleCount))
			
			#deferedBugsInCycle=sprintList+' AND type=Bug AND status != Closed'
			#totalOpenBugs=projectList+' AND type=Bug AND status !=Closed'
			
			#jiraBugs=getJiraProjectDefectCounts(jp)
			#bugCount={'totalSprint':0,'openSprint':0,'openCritical':0,'totalBacklog':0,'fromBacklog':0}
			
			sortOrder=' ORDER+BY+created+ASC++&src=confmacro'
		
			milestones=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_milestones/'+str(project['id'])+"&is_completed=0", headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			projectMilestones=milestones.json()
			
			results={'passed':0,'failed':0,'blocked':0,'untested':0}
			for milStn in projectMilestones:
				if not (milStn['name'].find(sprintName) > -1):
					msg="Ignoring Milestone: "+milStn['name']
					logAndPrint(fo, msg)
					projectMilestones.remove(milStn)
			
				elif " CI " in milStn['name']:
					msg="Ignoring Milestone: "+milStn['name']
					logAndPrint(fo, msg)
					projectMilestones.remove(milStn)
				
				else:
					runResults=getTestResultCount(project['id'],milStn['id'])
					for resultType in runResults:
						results[resultType]+=runResults[resultType]
					
			#print results
			
			totalTests=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_cases/'+str(project['id'])+'&custom_outdated=False', headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			testTotal=totalTests.json()
			totalTestCount=len(testTotal)
			#print "Tests: ",str(totalTestCount)
			
			totalAttempted=results['passed']+results['failed']+results['blocked']
			totalTests=totalTestCount #-obsoleteCount
			totalPassed=results['passed']
			openedBugs=0
			projectCertified=True

			className=jiraProject[0]
			
			nextProjectRow='<tr class="'+project['name']+'">'
			nextProjectRow+='<td colspan="1" class="'+className+'">'+project['name']+'</td>'
			nextProjectRow+='<td colspan="1" class="'+className+'ColA">'+str(totalTests)+'</td>'
			nextProjectRow+='<td colspan="1" class="'+className+'ColB">'+str(totalAttempted)+'</td>'
			nextProjectRow+='<td colspan="1" class="'+className+'ColC">'+'{:.2%}'.format(float(totalAttempted)/float(totalTests))+'</td>'
			if (totalAttempted < totalTests) : projectCertified=False
			nextProjectRow+='<td colspan="1" class="'+className+'ColD">'+str(totalPassed)+'</td>'
			nextProjectRow+='<td colspan="1" class="'+className+'ColE">'+'{:.2%}'.format(float(totalPassed)/float(totalTests))+'</td>'
			if (float(totalPassed)/float(totalTests) < .90) : projectCertified=False
			nextProjectRow+='<td colspan="1" class="'+className+'ColF"><a class="external-link" href="'+baseFilter+highPriorityBugs+'" rel="nofollow">'+str(highPriorityBugsCount)+'</a></td>'
			nextProjectRow+='<td colspan="1" class="'+className+'ColG"><a class="external-link" href="'+baseFilter+foundInCycle+'" rel="nofollow">'+str(foundInCycleCount)+'</a></td>'
			nextProjectRow+='<td colspan="1" class="'+className+'ColH"><a class="external-link" href="'+baseFilter+bugsResolved+'" rel="nofollow">'+str(bugsResolvedCount)+'</a></td>'
			nextProjectRow+='<td colspan="1" class="'+className+'ColI"><a class="external-link" href="'+baseFilter+bugsFromBacklog+'" rel="nofollow">'+str(bugsFromBacklogCount)+'</a></td>'
			nextProjectRow+='<td colspan="1" class="'+className+'ColJ"><a class="external-link" href="'+baseFilter+totalBacklog+'" rel="nofollow">'+str(totalBacklogCount)+'</a></td>'
			nextProjectRow+='<td colspan="1" class="'+className+'ColK">'+defPercent+'</td>'
			nextProjectRow+='<td colspan="1" class="'+className+'ColL">'+defBacklogPercent+'</td>'
			if (foundInCycleCount>0):
				if (float(deferedCount)/float(foundInCycleCount)>.125): projectCertified=False
			if projectCertified:
				nextProjectRow+='<td colspan="1" class="'+project['name']+'ColM"><span><ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">Green</ac:parameter><ac:parameter ac:name="title">YES</ac:parameter><ac:parameter ac:name="subtle">true</ac:parameter></ac:structured-macro></span></td>'
			else:			
				nextProjectRow+='<td colspan="1" class="'+project['name']+'ColM"><span><ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">Red</ac:parameter><ac:parameter ac:name="title">NO</ac:parameter><ac:parameter ac:name="subtle">false</ac:parameter></ac:structured-macro></span></td>'


			nextProjectRow+='<td colspan="1" class="confluenceTd"><span> link here </span></td>'
			nextProjectRow+='</tr>'

			
			certification+=nextProjectRow




			
	certification+='</tbody></table></div>'
	
	promoTable+=promoTableClose
	
	pageTitle="Daily Certification"
	
	#updateConfluencePage(pageTitle, certification+promoTable)
	updateConfluencePage(pageTitle, certification)
	
	if (fo!=None):
		fo.close()		
	
	
if __name__ == '__main__':
    main()