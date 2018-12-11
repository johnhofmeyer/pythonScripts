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



APIHeaders={'Content-Type': 'application/json'}

green='"color: rgb(0,153,0);"'
yellow='"color: rgb(255,153,0);"'
red='"color: rgb(255,0,0);"'
grey='"color: rgb(240,240,240);"'
black='"color: rgb(255,255,255);"'

jenkinsUser="john.hofmeyer"
jenkinsAPIToken="7ef40b73178fe27db33af8aec620558e"
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

def getProductionReleaseMilestones(projectID):
	releases=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_milestones/'+projectID+"&is_completed=0", headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	releaseMilestones=releases.json()
	print releaseMilestones
	for milStn in releaseMilestones:
		print milStn
		print milStn['name']
		if not ( ("Release" in milStn['name']) or ("Patch" in milStn['name'] ) ):
			print "Ignoring Milestone: "+milStn['name']
			releaseMilestones.remove(milStn)

	return(releaseMilestones)
	
	
def createMilestone(projectID,milestoneName):
	unixDates=getSprintDaysUnix()
	unixStart=unixDates[0]
	unixEnd=unixDates[1]
	
	milestoneData={'name': milestoneName,'start_on': unixStart,'due_on':unixEnd}
									
	newMilestone=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/add_milestone/'+str(projectID), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'),data=json.dumps(milestoneData))

	return newMilestone.json()

def getActiveTestRuns(projectID):
	
	testRuns=[]
	milestones=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_milestones/'+projectID+"&is_completed=0", headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	projectMilestones=milestones.json()
	
	for milestone in projectMilestones:
		
		milestoneRuns=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_runs/'+projectID+"&milestone_id="+str(milestone['id']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
		testRailRuns=milestoneRuns.json()
		
		if (len(testRailRuns) > 0):
			for run in testRailRuns:
				testRuns.append(run)
		
	return(testRuns)

def updateTestRuns(projectID, projectMilestones,jiraTickets):
	
	## First capture all of the active test runs in a project
	testRuns=getActiveTestRuns(projectID)
	
	milestoneID=getProductionBugMilestone(projectMilestones)

	for jiraStory in jiraTickets['issues']:
		try:
			jiraID=jiraStory['key']
			summary=jiraStory['fields']['summary']
		except Exception as e:
			print e
			print jiraStory
			exit()
		
		runExists=False
		runID=0

		if (len(testRuns)>0):
			for run in testRuns:
				try:
					if (jiraID in run['name']): 
						runExists=True
						runID=run['id']
				except:
					print "FAILED TEST RUN"
					print run
			
		if (runExists == False):
			print "MISSED TEST RUN: "+jiraStory['key']
			
			
	
			summaryUpper=summary.upper()
			
			runName=jiraID+" "+summary
			storyDetails={'name':runName, 'description': 'Test run for Jira ticket: ['+jiraID+'](https://projects.mbww.com/browse/'+jiraID+')','milestone_id':str(milestoneID)}
			storyRun=requests.post('https://testrail.cadreon.com/testrail/index.php?/api/v2/add_run/'+projectID+"&milestone_id="+str(milestoneID), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'),data=json.dumps(storyDetails))
			newStory=storyRun.json()
			runLink=newStory['url']
			
			storyDetail=requests.get(jiraStory['self'], headers=APIHeaders, auth=jiraAuth(),timeout=None)
			details=storyDetail.json()
			
			if details.has_key('fields'):
				if details['fields'].has_key('description'):
					description=details['fields']['description']+"\n\n(+) *Test Coverage:*\n"+runLink
					descriptionUpdate=json.dumps({"fields": {"description": description}})

					updateJira=requests.put("https://projects.mbww.com/rest/api/2/issue/"+jiraID, data=descriptionUpdate, headers=APIHeaders, auth=jiraAuth())
					
					
			else:
				description="\n\n(+) *Test Coverage:*\n"+runLink		
					
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

	return (0)	
		
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
	
def getConfluencePage(pageTitle):
	confluencePage=requests.get("https://wiki.mbww.com/rest/api/content?title="+pageTitle+"&expand=body.view,version,extensions.ancestors", headers={'Content-Type': 'application/json'}, auth=jiraAuth())	
	if (confluencePage.status_code > 299):
		print "Cannot Find: "+pageTitle
		exit()
	return(confluencePage.json())

def updateConfluencePage(contentPath, pageVersion, pageTitle, pageContent):
	confluencePutBody = json.dumps({u"version": {u"number": pageVersion},u"title": pageTitle,u"type": u"page",u"body": {u"storage": {u"value": pageContent,u"representation": u"storage"}}})
	confluenceUpdate=requests.put("https://wiki.mbww.com"+contentPath,data=confluencePutBody, headers={'Content-Type': 'application/json'}, auth=jiraAuth())
	if (confluenceUpdate.status_code > 200):
		print confluencePutBody
		print confluenceUpdate.raise_for_status()
	return(confluenceUpdate.status_code)

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
	
	# capture the metrics, related to defects
	#if (sprintYesterday > -1):
	#	projectCursor.execute("SELECT newDefects, inDev, reopened, inReview, inQA, verified, closed from defects WHERE sprint_number = "+sprintNumber+" and sprint_day = "+str(sprintYesterday)+" and jira_project = '"+project+"'; ",)
	#	for (newDefects,inDev,inReview,inQA,reopened,verified,closed) in projectCursor:
	#		if newDefects is None: newDefects=0
	#		if inDev is None: inDev=0
	#		if inReview is None: inReview=0
	#		if inQA is None: inQA=0
	#		if reopened is None: reopened=0
	#		if verified is None: verified=0
	#		if closed is None: closed=0
	#		if reopened is None: reopened=0
			
	#		defectStatus["New"]["yesterday"]=newDefects
	#		defectStatus["In Progress"]["yesterday"]=inDev
	#		defectStatus["In Review"]["yesterday"]=inReview
	#		defectStatus["Resolved"]["yesterday"]=inQA
	#		defectStatus["Reopened"]["yesterday"]=reopened
	#		defectStatus["Verified"]["yesterday"]=verified
	#		defectStatus["Closed"]["yesterday"]=closed
	#		defectStatus["Reopened"]["yesterday"]=reopened
	
	return defectStatus

def getJiraTicket(jiraID):
	if (validJiraId(jiraID)):
		storyFilter='{"jql":"Id = '+jiraID+'","fields":["id","key","priority","created","summary","status","reporter"]}'
		storyQuery=requests.post("https://projects.mbww.com/rest/api/2/search", data=storyFilter, headers=APIHeaders, auth=jiraAuth())
		try:
			jiraStory=storyQuery.json()
		except Exception as e:
			print "failed to get story id",jiraID
			print storyQuery
			print e
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
	if ("jira=" in projAnnouncement):

		jiraId=projAnnouncement.split("jira=")[1].split()[0]
		if (jiraId.find(",") > -1):
			
			jiraIdList=[]
			for jirId in jiraId.split(","):
				jiraIdList.append(jirId)
					
			return(jiraIdList)
		else:
			return(jiraId)

	return(None)
	
def logAndPrint(theLog,message):
	try:
		if (theLog != None):
			theLog.writelines(message+chr(13))
		
		printOut=message.split(chr(13))
		for lineOut in printOut:
			print lineOut+'\r\n'
	except Exception as e:
		print "**** FAILURE in LOGGING ****"
		print e
	
	return

def main():
	# capture script input options, for future use
	cmdOptions = sys.argv
	
	sep=chr(47)
	fo=None
	
	if ("jenkins" not in cmdOptions) or ("scheduled" not in cmdOptions):
		fileName="C:"+sep+"Users"+sep+"John.Hofmeyer"+sep+"Desktop"+sep+"testCoverage.txt"
		fo=open(fileName,'w')	
	
	regionSpecific=getCommandValue("region")
	
	jiraAuth=HTTPBasicAuth('john.hofmeyer@mbww.com',getNetworkAuth())
	updateResults=True
	
	# Connect to coverage database
	db=mysql.connector.connect(user='daily_stats', password='yVgvQM7NU&vJXj6637D9',host='qa-daily-stats.ckvgpujcycok.us-east-1.rds.amazonaws.com',database='coverage',buffered=True)

	cursor=db.cursor()
	subCursor=db.cursor()
	
	# define queries for test coverage results
	count_query= ("SELECT Count(*) from results WHERE sprint_number = %s and sprint_day = %s and project = %s and run_name = %s ;")
	# count data = sprint_number, sprint_day, project, run_name
	
	# both the INSERT and UPDATE queries use the same data set
	# data=passed, failed, blocked, untested, sprint_number, sprint_day, project, run_name
	
	insert_defects=("INSERT INTO defects "
					"(sprint_number, sprint_day, jira_project, newdefects, indev, reopened, inreview, inqa, verified, closed, totalopen) "
					"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" )
	
	update_defects=("UPDATE defects"
					"SET newdefects = %s, indev = %s, reopened = %s, inreview = %s, inqa = %s, verified = %s, closed = %s, totalopen = %s"
					"WHERE sprint_number= %s and sprint_day=%s and project =%s"
					"VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
	
	insert_result=("INSERT INTO results "
               "(passed, failed, blocked, untested, sprint_number, sprint_day, project, run_name, test_type, jira_status, jira_points, due_date, bug_count, testcase_total) "
               "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
			   
	update_result=("UPDATE results "
				   "SET passed = %s , failed = %s , blocked = %s , untested = %s"
				   "WHERE sprint_number = %s AND sprint_day = %s AND project= %s AND run_name = %s and test_type = %s"
				   "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)")
	
	
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
	
	msg= "Current Sprint: "+str(currentSprint)
	logAndPrint(fo,msg)
	msg= "Sprint Day #"+str(sprintDay+1)
	logAndPrint(fo,msg)

	dateToday=date(datetime.today().year,datetime.today().month,datetime.today().day)
	if (sprintDay == 0) or (sprintDay==5):
		dateYesterday=dateToday-timedelta(days=3)
	else:
		dateYesterday=dateToday-timedelta(days=1)
	

	

	

	################
	##
	##  Define dictionaries for test cases
	projectJiraDict={}
	jiraStatusDict={}
	regionDict={}
	regionRegress={}
	
	dueDate=""
	
	resultText={'1':'passed','2':'blocked','3':'untested','4':'Retest','5':'Failed','6':'In Progress','7':'Untested-Late','8':'Untested n/a','10':'Passed-Support','11':'Passed-Stage','12':'Passed-Production'}

	totalAutomated=0
	totalTestCount=0
	regionList = []
	projectList=[]
	
	regionInclude=getCommandValue("region")
	skipProjects=getCommandValue("skip")
	
	## Get all of the project info in one object
	allProjects=db.cursor()
	ciJobs=db.cursor()
	
	allProjQuery="SELECT * FROM projectmapping;"
	allProjects.execute(allProjQuery, '')
	
	for project in allProjects:
		jira_project=str(project[0])
		jiraProjectName=str(project[1])
		jira_id=str(project[2])
		testrailProjectName=str(project[3])
		testrail_id=str(project[4])
		ci_path=str(project[5])
		region=str(project[6])
		
		if projectJiraDict.has_key(testrail_id):
			jProjectList=[]
			jProjectList.append(projectJiraDict[testrail_id]['jiraProject'])
			jProjectList.append(jira_project)
			projectJiraDict[testrail_id]={"jiraName":jiraProjectName, "jiraProject":jProjectList, "testrailName": testrailProjectName,"testrailID": testrail_id, "region":region}
			print "Added JiraProject: "+jira_project+" to: "+testrailProjectName
		else:
			projectJiraDict[testrail_id]={"jiraName":jiraProjectName, "jiraProject":jira_project, "testrailName": testrailProjectName,"testrailID": testrail_id, "region":region}
	
	
	##########
	##
	##  Capture project data from Testrail and update the allProject dictionary
	##
	##########
	'''
	projects=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_projects&is_completed=0', headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	testRailProjects=projects.json()
	for proj in testRailProjects:
		## determine if the jira ID is included in the testrail project description
		if (proj['announcement'] != None): 
			trId=str(proj['id'])
			trName=proj['name']
			
			if isinstance(getJiraIDFromTestrail(proj['announcement']), list):
				print trName+" has multiple Jira projects"
				### Remove duplicate jira entries
				jiraList=getJiraIDFromTestrail(proj['announcement'])
				## Determine parent project in projectJiraDict
				if projectJiraDict.has_key(trId):
					for jItem in jiraList:
						if jItem not in projectJiraDict[trId]['jiraProject']:
							projectJiraDict[trId]['jiraProject'].append(jItem)
							print "Added Jira "+jItem+" to "+trName
				else:
					print "NEED TO ADD Testrail - jira assignment to database"
			######
			## If there is a single Jira project associated to the testrail project
			#####	
			
			else:
				jiraID=getJiraIDFromTestrail(proj['announcement'])
				if projectJiraDict.has_key(trId):
					if (projectJiraDict[trId]['jiraProject'] != jiraID):
						print "***** Testrail "+projectJiraDict[trId]['testrailName']+" and Jira Project "+projectJiraDict[trId]['jiraProject']+" are out of Sync"
				
				else:
					projectJiraDict[trId]={"jiraName":trName, "jiraProject":jiraID, "testrailName": trName,"testrailID": trId, "region":"unknown"}

					## update the project in the database
					insertProject=("INSERT INTO projectmapping (jira_project, project, project_name, testrail_id) VALUES (%s, %s, %s, %s)")
					insertData=(jiraID, trName, trName, str(trId))
					allProjects.execute(insertProject, insertData)
					db.commit()
					print "New Project added: "+trName

					print "project mapping table updated with: "+jiraID+" for Testrail project: "+trName
					print "Check for labels in the testrail description to determine which labels determine test case population"
					
	'''
	CI={}
	components={}
	allCIQuery="SELECT project, component, cipath from componentmapping where cipath is Not Null;"
	ciJobs.execute(allCIQuery, '')
	
	for job in ciJobs:
		if CI.has_key(job[0]):
			CI[job[0]][job[1]]=job[2]
		else:
			CI[job[0]]={job[1]:job[2]}


		#if (str(projectInfo[4]) not in (skipProjects)):
		#
		#	if  (regionInclude is False):
		#		projectList.append(str(projectInfo[4]))
		#	else:
		#		if (getCommandValue("region") == projectInfo[6]):
		#			projectList.append(str(projectInfo[4]))
	
	## Get a list of all of the regions
	regions=db.cursor()
	regionQuery="SELECT DISTINCT(region) from projectmapping;"
	regions.execute(regionQuery, '')
	
	for country in regions:
		regionList.append(country)
	
	
	############################################################
	##
	##  Main loop - cycle through each project
	##
	##	Obsolete test type id: 16
	
	
	# Get the list of all projects in TestRail
	# projects=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_projects&is_completed=0', headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	# testRailProjects=projects.json()
	exceptProject=["17", "26", "27", "29", "30", "51"]
	for project in projectJiraDict:
		milestoneCount=0
		milestones=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_milestones/'+project+"&is_completed=0", headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
		activeMilestones=milestones.json()
		for activeMilestone in activeMilestones:
			if (activeMilestone['name'].find(sprintName) > -1): milestoneCount+=1
		
		if (milestoneCount==0):
			#print str(project)
			exceptProject.append(str(project))
			
	for project in projectJiraDict:

		projectID = project
		
		region=projectJiraDict[project]['region']
		jiraProject=projectJiraDict[project]['jiraProject']
		
		getActiveTestRuns(project)
		###################################################################
		##
		##	Exclude Test Projects
		##
		
		if (projectID not in exceptProject ):
		## In-Channel is 52
		## (region == regionSpecific) and
		#if (str(projectID) in projectList):
			
		  
			milestones=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_milestones/'+projectID+"&is_completed=0", headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			projectMilestones=milestones.json()
			for milStn in projectMilestones:
				if not (milStn['name'].find(sprintName) > -1):
					msg="Ignoring Milestone: "+milStn['name']
					logAndPrint(fo, msg)
					projectMilestones.remove(milStn)
			
				elif " CI " in milStn['name']:
					msg="Ignoring Milestone: "+milStn['name']
					logAndPrint(fo, msg)
					projectMilestones.remove(milStn)
			
			mstoneId=-1
			mstoneName="undefined"
			
			## If an error occurs in capturing the count, the value is 0
			regressionTestCount=getTotalRegressionTestCount(projectID)
			
			## obsolete tests needs an update
			obsoleteTests=getObsoleteTestcount(projectID)
			
			#################################################################
			##
			##  Determine total tests created, since first day of the Sprint
			##
			
			#newTests=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_cases/'+projectID+"&created_after="+str(firstDayUnix), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			#projectTests=newTests.json()
			
			## New Project Ticket Table
			projectTicketTable=getTicketTableHeader()

			#projQuery="SELECT jira_project,region FROM projectmapping WHERE project='"+project['name']+"';"
			#subCursor.execute(projQuery, (project['name']))
			#for (jira_project) in subCursor:
			#	jiraProjectName=jira_project[0]
			
			autoRegression=[0,0,0,0]
			jiraProject=projectJiraDict[project]['jiraProject']
			
			logAndPrint(fo," ")
			logAndPrint(fo,"#############################################################################")
			msg= "## Project: "+projectJiraDict[project]['testrailName']
			logAndPrint(fo,msg)
			logAndPrint(fo,"#############################################################################")
			logAndPrint(fo,"Regression test count: "+str(regressionTestCount))
			logAndPrint(fo,"Number tests marked obsolete: "+str(obsoleteTests))
			
			for currentMilestone in projectMilestones:
				milestoneDescription=""
				# If the milestone is current - then review the test runs associated to the milestone
				if (currentMilestone['name'].find(sprintName+" - Feature Scenarios") > -1):
				
					## if jiraProjectName has not been defined, determine all of the project related info
					#if (jiraProjectName!=""):
					if isinstance(projectJiraDict[project]['jiraProject'], list):
						jiraProjectName=projectJiraDict[project]['jiraProject'][0]
						#for jiraProjectName in projectJiraDict[project]['jiraProject']:
					else:
						jiraProjectName=jiraProject
					 
					## Get Production defects for the project
					#if (currentMilestone['name'].find("Scenarios") > -1):
					if isinstance(projectJiraDict[project]['jiraProject'], list):
						prodBugs={}
						for jiraProjectName in projectJiraDict[project]['jiraProject']:
							productBugs=getRecentProductionBugs(jiraProjectName)
							if productBugs.has_key('total'):
								if productBugs['total'] > 0:
									if (prodBugs == {}):
										prodBugs=getRecentProductionBugs(jiraProjectName)
									else:
										prodBugs['total']+=productBugs['total']
										prodBugs['issues'].append(productBugs['issues'])
						
						print prodBugs
						
					else:
						prodBugs=getRecentProductionBugs(jiraProjectName)
						
						
						
					if (prodBugs.has_key('total')):
						totalProdBugs=prodBugs['total']
						if (totalProdBugs > 0):
						
							logAndPrint(fo,"### Production Bugs ###")
							#updateTestRuns(projectID,prodBugMilestone,prodBugs)
							updateTestRuns(projectID,projectMilestones,prodBugs)
							
							for pBug in prodBugs['issues']:
								try:
									msg=pBug['fields']['created'].split("T")[0]+" "+pBug['key']+" "+pBug['fields']['summary']
								except:
									print pBug
								logAndPrint(fo, msg)
					
							#### Check for Production bug milestone
							
					
					## Get CI Stats for the project
					tableCI=None
					for app in CI:
						if (app == jiraProject):
							tableCI=getCITableHeader()
							for component in CI[app]:
								latestBuild=0
								oldestBuild=-1
								failedCount=0
								passCount=0
								ciPath=CI[app][component].split('https://jenkins.cadreonint.com')[1]
								#ciPath=jenkinsHost+ciPath+"/api/json"
								ciPath=jenkinsHost+ciPath+"/rssAll"
								
								ciBuilds=feedparser.parse(ciPath)
								currentStatus='red'
								for eachEntry in ciBuilds['entries']:
									if str(dateToday) in str(eachEntry['updated']) or str(dateYesterday) in str(eachEntry['updated']):

										#print eachEntry['updated']
										#print eachEntry['title']
										
										build=eachEntry['title'].split("#")[1].split("(")[0]
										status=determineCIStatus(eachEntry['title'])
										if (oldestBuild <0) or (oldestBuild>build):
											oldestBuild=build
										
										
										if (build>latestBuild):
											latestBuild=build
											currentStatus=status
										
										failedCount+=(status=='red')
										passCount+=(status=='green')
								
								ciStatus='<td class="highlight-green confluenceTd" data-highlight-colour="'+currentStatus+'">'+str(latestBuild)+'</td>'
								if (failedCount == 0) and (currentStatus == 'green'):
									sinceBuild='<td class="highlight-green confluenceTd" data-highlight-colour="green">'+str(oldestBuild)+'</td>'
									passfail='<td class="highlight-green confluenceTd" data-highlight-colour="green">'+str(passCount)+'</td><td>0</td>'
								else:
									sinceBuild='<td>'+str(oldestBuild)+'</td>'
									passfail='<td class="highlight-green confluenceTd" data-highlight-colour="green">'+str(passCount)+'</td><td class="highlight-red confluenceTd" data-highlight-colour="red">'+str(failedCount)+'</td>'
								
								tableCI+='<tr><td>'+component+'</td>'+ciStatus+sinceBuild+passfail+'</tr>'
								

								
								print "CI Status: ",currentStatus," | Build: ",latestBuild
								print "Status since Build: ",oldestBuild
								print "Pass: ",str(failedCount)," Failed: ",str(failedCount)
								
								
								
							tableCI+='</tbody></table></div>'
							#exit()
					
					## Get Total Bug Count for project
					if isinstance(projectJiraDict[project]['jiraProject'], list):
						openBugs={}
						for jiraProjectName in projectJiraDict[project]['jiraProject']:
							prodBugs.update(getAllOpenBugs(jiraProjectName))
					else:
						openBugs=getAllOpenBugs(jiraProjectName)
					openBugsTotal=0
					if (openBugs.has_key('total')):
						openBugsTotal=openBugs['total']
					
					## Get Count of bugs Closed this Sprint

					closedBugCount=getClosedSprintBugs(projectJiraDict[project]['jiraProject'])
					
					## Get Sprint bugs Reported this Sprint		
					sprintBugs=getSprintBugs(jiraProjectName)
					# bugs found in sprint = sprintBugs['total']
					
					sprintBugStatus={}
					logAndPrint(fo,"### Sprint Bugs ###")
					bugTotal=0
					if (sprintBugs.has_key('total')):
						for bug in sprintBugs['issues']:
						
							## Get bug details
							bugDetail=getJiraDetails(bug['key'])
							if (bugDetail == None):
								bugDetail=""
							print bug['key']
							print bugDetail
							logAndPrint (fo, bug['key']+"\t related to: "+bugDetail)
							
							## Bug status
							status=bug['fields']['status']['statusCategory']['name']
							if (sprintBugStatus.has_key(status)):
								sprintBugStatus[status]+=1
							else:
								sprintBugStatus[status]=1
					
						bugStats=""
						for bugType in sprintBugStatus:
							bugTotal+=sprintBugStatus[bugType]
							bugStats+="\t"+bugType+":"+str(sprintBugStatus[bugType])
					else:
						bugStats="No Bugs"
					
					logAndPrint(fo,bugStats)
				
					try:
						projectPage=getConfluencePage(projectJiraDict[project]['testrailName']+" Test Coverage")
					except:
						print "Cannot find wiki page for: "+projectJiraDict[project]['testrailName']+" Test Coverage"
						print projectPage
						print project
						exit()
						
					#confluencePageId=projectPage['results'][0]['id']
					## Some exception handling - in case the page is not in confluence or confluence decides to kick us out
					pageInfoList=getDictionaryValue(projectPage,'results')
					try:
						pageInfo=pageInfoList[0]
					except:
						print "*** Exception in parsing the project page ***"
						print projectJiraDict[project]['testrailName']+" Test Coverage"
						print pageInfoList
						print project
						#exit()
						
					#pageVersion=pageInfo['version']['number']
					pageVersionDict=getDictionaryValue(pageInfo,'version')
					pageVersion=getDictionaryValue(pageVersionDict,'number')
					
					#contentPath=projectPage['results'][0]['version']['_expandable']['content']
					expandableContent=getDictionaryValue(pageVersionDict,'_expandable')	
					contentPath=getDictionaryValue(expandableContent,'content')
					
					
					#confluencePageTitle=projectPage['results'][0]['title']
					confluencePageTitle=pageInfo['title']
					
					updatedVersion=pageVersion+1
					
					confluenceContent=createProjectPage(projectJiraDict[project]['testrailName']+" Test Coverage")
					confluenceContent+=addProductionBugs(prodBugs)
					if (tableCI != None):
						confluenceContent+=tableCI
					confluenceContent+=addSprintBugs(sprintBugs)
				
				
				if (currentMilestone['name'].find("Feature Scenarios") > -1) or (currentMilestone['name'].find("Regression") > -1):
					## Determine test type, based on milestone
					testType="manual"
					if (currentMilestone['name'].find("Feature") > -1):
						testType="feature"
					if (currentMilestone['name'].find("Automated") > -1):
						testType="automated"
					
					milestoneID=currentMilestone['id']
					runs=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_runs/'+projectID+"&milestone_id="+str(milestoneID)+"&is_completed=0", headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
					projectRuns=runs.json()
					
					if (testType=="feature"):
						logAndPrint(fo," ")
						sep="\t\t"+"*"*(len(currentMilestone['name'])+14)
						logAndPrint(fo,sep)
						msg="\t\t** Milestone: "+currentMilestone['name']
						logAndPrint(fo,msg)
						logAndPrint(fo,sep)
					
					for run in projectRuns:
						## only include automated regression for current sprint day
						
						if (testType=="automated") and not(run['name'].find(dateString)>-1) :
							print "skipping: "+run['name']

						else:
							count_data=(currentSprint, sprintDay, projectJiraDict[project]['testrailName'], run['name'])
							cursor.execute(count_query,count_data)
							
							jiraDetails=""
							jiraInfo=["","","","",""]
							if (testType=="feature"):
								jiraID=run['name'].split(" ")[0]
								jiraInfo=getJiraDetails(jiraID)
								
								if (jiraInfo == None):
									msg="Milestone: "+currentMilestone['name']+" Jira Info is empty: "+jiraID
									logAndPrint(fo,msg)
								
								elif (jiraInfo[0]=="error"):
									logAndPrint(fo,jiraInfo[1])
								else:
									jiraDetails="\n\tStatus: "+jiraInfo[0]+"\tPoints: "+jiraInfo[1]+"\tDue Date: "+jiraInfo[2]+"\tBug Count: "+str(jiraInfo[3])
									jiraStatus=jiraInfo[0]
									jiraPoints=jiraInfo[1]
									dueDate=jiraInfo[2]
									bugCount=str(jiraInfo[3])				
							
							try:
								passedCount=run['passed_count']
								failedCount=run['failed_count']
								blockedCount=run['blocked_count']
								untestedCount=run['untested_count']
								if (run['include_all']):
									passedCount=0
									failedCount=0
									blockedCount=0
									untestedCount=0
							except:
								"Test Run failure"
								print run
								print jiraInfo
								exit()
							
							if (jiraInfo !=None) and (len(jiraInfo) > 3):
								query_data=(passedCount, failedCount, blockedCount, untestedCount, currentSprint, sprintDay, projectJiraDict[project]['testrailName'], run['name'], testType, jiraInfo[0], jiraInfo[1], jiraInfo[2], jiraInfo[3], regressionTestCount)
							
							if (testType=="automated"):
								autoRegression[0]+=passedCount
								autoRegression[1]+=failedCount
								autoRegression[2]+=blockedCount
								autoRegression[3]+=untestedCount
									
							
							
							
							for rowCount in cursor:
								try:
									resultCount=rowCount[0]
								except:
									print cursor
							
							if (resultCount>0):
	
								try:
									if (testType=="feature"):	

										cursor.execute("UPDATE results "
													   "SET passed = "+str(passedCount)+" , failed = "+str(failedCount)+" , blocked = "+str(blockedCount)+" , untested = "+str(untestedCount)+" , jira_status = "+jiraStatus+" , jira_points = "+jiraPoints+" , due_date = "+dueDate+" , bug_count = "+str(jiraInfo[3])+" , testcase_total = "+str(regressionTestCount)+""
													   "WHERE sprint_number = "+str(currentSprint)+" AND sprint_day = "+str(sprintDay)+" AND project= "+(projectJiraDict[project]['testrailName'])+" AND run_name = "+run['name']+" AND test_type = "+testType+"",
													   "VALUES (%s)",str(passedCount))
									else:
										cursor.execute("UPDATE results "
													   "SET passed = "+str(passedCount)+" , failed = "+str(failedCount)+" , blocked = "+str(blockedCount)+" , untested = "+str(untestedCount)+" , testcase_total = "+str(regressionTestCount)+""
													   "WHERE sprint_number = "+str(currentSprint)+" AND sprint_day = "+str(sprintDay)+" AND project= "+(projectJiraDict[project]['testrailName'])+" AND run_name = "+run['name']+" AND test_type = "+testType+"",
													   "VALUES (%s)",str(passedCount))
								#except cursor.execute.Error as err:
								except:
									"Problem updating database for: "+projectJiraDict[project]['testrailName']
									#print (err)
								
							else:
								# INSERT
								cursor.execute(insert_result, query_data)
							db.commit()
							
							exceptionmsg=""
							if (jiraInfo == None): testType="unsupported"
							if (len(jiraInfo)<4):
								testType="invalid"
								
							if (testType=="feature"):
							
								testCount=passedCount+failedCount+blockedCount+untestedCount
								testStatus="Due: "+dueDate
								ticketStatus=jiraStatus

								## unexecuted tests
								
								if (jiraInfo[0] == "Resolved") and (run['untested_count'] > 0):
									testStatus=str(untestedCount)+' unexecuted test'
									if (untestedCount>1):testStatus+='s'
									#if (sprintDay>1):
										#cursor.execute("SELECT jira_status from results where run_name = "+run['name'])+" AND sprint_number = "+str(currentSprint)+" AND sprint_day = "+str(sprintDay-1)+"",run['name')]
									exceptionmsg+="** UNEXECUTED TESTS: "+str(untestedCount)+" **\n"
								
								## No Due date - or Past due
								if (str(dueDate) == "None"):
									if (sprintDay>1):
										exceptionmsg+="*** Story has No Due Date ***\n"
										ticketStatus="MISSING DUE DATE "+jiraStatus
										
								## Due Date is not blank, check if the Ticket is still under development
								elif (jiraStatus in ("To Do", "In Progress", "Ready")):
									ticketDue=date(int(dueDate.split("-")[0]),int(dueDate.split("-")[1]),int(dueDate.split("-")[2]))
									if (ticketDue<dateToday):
										dueDateDifference=str(dateToday-ticketDue).split(",")[0]
										exceptionmsg+="*** STORY LATE BY "+dueDateDifference+" ***\n"
										testStatus="STORY LATE "+dueDateDifference
										if ("1" not in dueDateDifference):
											ticketStatus='<td class="highlight-red confluenceTd" data-highlight-colour="red"><b>'+jiraStatus+'</b></td>'
										#ticketStatus=jiraStatus
								
								## No Story Points
								if ( jiraPoints < 1):
									exceptionmsg+="*** NO STORY POINTS ***\n"
									if (jiraStatus in ("To Do", "In Progress", "Ready")):
										ticketStatus='<td class="highlight-red confluenceTd" data-highlight-colour="red"><b>NO STORY POINTS </b>'+jiraStatus+'</td>'
								
								## Story is Done
								if (jiraInfo[4] != "") and (jiraStatus=="Resolved") and (jiraInfo != None):
									jiraDone=jiraInfo[4].split("T")
									doneTime=getTwelveHourTime(jiraDone[1])
									doneDay=date(int(jiraDone[0].split("-")[0]),int(jiraDone[0].split("-")[1]),int(jiraDone[0].split("-")[2]))
									
									if (doneDay == date.today()):
										ticketStatus="Done Today at "+doneTime
									else:
										doneLength=abs(int(str(doneDay-date.today()).split()[0]))
										if (doneLength==1):
											ticketStatus="Done Yesterday at "+doneTime
										else:
											ticketStatus="Done "+str(doneLength)+" days ago"
								
								## Failed tests but no Bugs
								if (failedCount>0) and (bugCount == "0"):
									exceptionmsg+="**** FAILED TESTS WITH NO BUGS ASSOCIATED TO STORY ****\n"
									testStatus='<td class="highlight-red confluenceTd" data-highlight-colour="red">FAILED TESTS - <b>MISSING BUGS</b></td>'
								
								## No Scenarios
								if (testCount) < 1:
									testStatus='<td class="highlight-red confluenceTd" data-highlight-colour="red"><b>!! NO SCENARIOS !!</b></td>'
									exceptionmsg+="***** !!!   NO ASSOCIATED SCENARIOS  !!!  *****\n"
								
								#testing complete!
								if (untestedCount<1) and (passedCount==testCount) and (testCount>0) and (testStatus==("Due: "+dueDate)):
									testStatus='<td class="highlight-green confluenceTd" data-highlight-colour="green">tested</td>'
								
								if ('<td' not in testStatus):
									testStatus='<td>'+testStatus+'</td>'
								if ('<td' not in ticketStatus):
									ticketStatus='<td>'+ticketStatus+'</td>'
								
								## ticketRow does NOT include the <tr> and </tr> markup
								ticketRow='<td><a class="external-link" href="https://projects.mbww.com/browse/'+jiraID+'" rel="nofollow" target="_blank" data-ext-link-init="true">'+jiraID+'</a></td>'
								ticketRow+='<td>'+str(jiraPoints)+'</td>'
								ticketRow+=ticketStatus
								ticketRow+=testStatus
								ticketRow+='<td>'+str(passedCount)+'</td>'
								ticketRow+='<td>'+str(failedCount)+'</td>'
								ticketRow+='<td>'+str(blockedCount)+'</td>'
								ticketRow+='<td>'+str(untestedCount)+'</td>'
								ticketRow+='<td>'+bugCount+'</td>'
								
								if ("green" in testStatus) or ("Due: " in testStatus):
									pass # no need to add this row
								else:
									regionRow='<tr><td>'+projectJiraDict[project]['testrailName']+'</td>'+ticketRow+'</tr>'
									if regionDict.has_key(region):
										regionDict[region] = regionDict[region]+regionRow
									elif (len(region)>1):
										regionDict[region]=getTicketTableHeader("region")+regionRow
									
								
								projectTicketTable+='<tr>'+ticketRow+'</tr>'						
								
								msg=exceptionmsg+run['name']+ "\n\tPassed:\t"+str(passedCount)+"\tFailed:\t"+str(failedCount)+"\tBlocked:\t"+str(blockedCount)+"\tUntested:\t"+str(untestedCount)+"\tTest Type:\t"+testType
								msg+=jiraDetails
								logAndPrint(fo,msg)
							
					logAndPrint(fo," ")
				#print regionDict
			
			## UPDATE Project Page in Confluence
			
			if (jiraProjectName!="") and (projectID not in ("6", "9", "40", "45", "46")):
				regressionRow='<td>'+str(autoRegression[0])+'</td>'
				regressionRow+='<td>'+str(autoRegression[1])+'</td>'
				regressionRow+='<td>'+str(autoRegression[2])+'</td>'
				regressionRow+='<td>'+str(autoRegression[3])+'</td>'
				regressionRow+='<td>'+str(regressionTestCount)+'</td>'
			
				regressionTable=getRegressionTableHeader()
				regressionTable+='<tr>'+regressionRow+'</tr></tbody></table></div>'
				
				if regionRegress.has_key(region):
					regionRegress[region] = regionRegress[region]+'<tr><td>'+projectJiraDict[project]['testrailName']+'</td>'+regressionRow+'</tr>'
				elif (region!=""):
					regionRegress[region]=getRegressionTableHeader("region")+'<tr><td>'+projectJiraDict[project]['testrailName']+'</td>'+regressionRow+'</tr>'
				
				projectTicketTable+='</tbody></table></div>'
				
				confluenceContent+=regressionTable+projectTicketTable
				
				confluenceResponseCode=updateConfluencePage(contentPath, updatedVersion, confluencePageTitle, confluenceContent)
				if (confluenceResponseCode > 299):
					print "!! Page: "+confluencePageTitle+" Response code: "+str(confluenceResponseCode)
				                     
	## Let's figure out our progress!
	## Progress in this Sprint
	#Total Story Points by Status
	
	dailyExecutionQuery='select project, sum(passed + failed) as "Executed Tests", sum(passed + failed + blocked + untested) as "Total Feature Tests", sum(passed + failed)/sum(passed + failed + blocked + untested) as "Percent" from results where sprint_number='+str(currentSprint)+' and sprint_day='+str(sprintDay)+' and test_type="feature" group by project order by Percent;'
	dailyAutomationQuery='select project, sum(passed + failed + blocked + untested) as "Total Automated", testcase_total as "Total Tests", sum(passed + failed + blocked + untested)/testcase_total as "Percent" from results where sprint_number='+str(currentSprint)+' and sprint_day='+str(sprintDay)+' and test_type="automated" group by project order by Percent;'
	
	cursor.execute(dailyExecutionQuery, '')
	for row in cursor:
		logAndPrint(fo, row)
	
	cursor.execute(dailyAutomationQuery, '')
	for row in cursor:
		logAndPrint(fo, row)
	
	executionDict={}
	executionQuery='select sprint_day, project, passed, failed, blocked, untested from results where sprint_number='+str(currentSprint)+' and test_type="feature" order by sprint_day;'
	cursor.execute(executionQuery, '')
	
	for qr in cursor:
		# qr[0] = sprint_day
		# qr[1] = project 
		testStatusDict={'passed':qr[2],'failed':qr[3],'blocked':qr[4],'untested':qr[5]}
		
		if executionDict.has_key(qr[1]):				# qr[1] = project, if the project exists
			if executionDict[qr[1]].has_key(qr[0]): 	# qr[0] = sprint_day key exists
				for testKey in executionDict[qr[1]][qr[0]].keys():
					updatedValue=executionDict[qr[1]][qr[0]][testKey]+testStatusDict[testKey]
					executionDict[qr[1]][qr[0]][testKey]=updatedValue

			else:	# new sprint day for this project
				executionDict[qr[1]][qr[0]]=testStatusDict
				
		else:
			executionDict[qr[1]]={qr[0]:testStatusDict}
	
	trendTable=getTrendTableHeader("region")
	for product in executionDict:
		
		for theDay in executionDict[product]:
			trendTable+='<tr><td>'+product+'</td><td>'+str(theDay)+'</td><td>'+str(executionDict[product][theDay]['passed'])+'</td><td>'+str(executionDict[product][theDay]['failed'])+'</td><td>'+str(executionDict[product][theDay]['blocked'])+'</td><td>'+str(executionDict[product][theDay]['untested'])+'</td></tr>'
			
	trendTable+='</tbody></table></div>'
	#print executionDict
			
	cursor.close()
	db.close()

	for country in regionList:
		prodRegion=str(country[0]).replace("'","")
		if (prodRegion != ''):
			## Production issues, CI, and Regression status should go here
			
			## Load the confluence page, update and save
			print prodRegion

			regionPage=getConfluencePage(prodRegion+" Test Coverage")
			
			if regionPage.has_key('results'):

				regionResults=regionPage['results'][0]	# regionResults is a dictionary object
				if regionResults.has_key('version'):
					print "\n"
					print "VERSION"
					print regionResults['version']['number']
					print "\n"
				
			
			regionResults=regionPage['results'][0]
			
			regionPageVersion=regionResults['version']['number']
			print "Version: ",regionPageVersion
			
			updatedRegionVersion=regionPageVersion+1
			print "New Version: ",updatedRegionVersion
			
			contentPath=regionResults['version']['_expandable']['content']
			#contentPath=regionPage['results'][0]['version']['_expandable']['content']
			print "path: ",contentPath
			
			confluencePageTitle=regionResults['title']
			print "Title: ",confluencePageTitle
			
			#regionRegress[region] = regionRegress[region]+'</tbody></table></div>'
			
			#print regionRegress[region]
			#print regionDict[prodRegion]
			
			if regionRegress.has_key(prodRegion):
				if regionDict.has_key(prodRegion):
					regionContent=regionRegress[prodRegion]+'</tbody></table></div>'+regionDict[prodRegion]+'</tbody></table></div>'
				else:
					regionContent=regionRegress[prodRegion]+'</tbody></table></div>'
			elif regionDict.has_key(prodRegion):
				regionContent=regionDict[prodRegion]+'</tbody></table></div>'
			
			regionContent+=trendTable
		 
			## Update the region page with the aggregate information
			conflunceRegionUpdate=updateConfluencePage(contentPath, updatedRegionVersion, confluencePageTitle, regionContent)
			print "Confluence Update"
			print conflunceRegionUpdate
				
			if (conflunceRegionUpdate > 299):
				print str(conflunceRegionUpdate.raise_for_status())
				print "!! Page: "+confluencePageTitle+" Response code: "+str(confluenceResponseCode)

				
				
	if (fo!=None):
		fo.close()		
	
	
if __name__ == '__main__':
    main()