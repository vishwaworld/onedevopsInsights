#-------------------------------------------------------------------------------
# Copyright 2017 Cognizant Technology Solutions
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations under
# the License.
#-------------------------------------------------------------------------------
'''
Created on Jun 22, 2016

@author: 463188
'''
from com.cognizant.devops.platformagents.core.BaseAgent import BaseAgent
import xml.etree.ElementTree as ET

class HpAlmAgent(BaseAgent):
    def getHpAlmSSOHeader(self, baseEndPoint):
        userid = self.config.get('userid')
        passwd = self.config.get('passwd')
        authEndPoint = baseEndPoint + '/qcbin/authentication-point/authenticate' 
        responseTupple = {}
        reqHeaders = {
                        "Content-Type" : "application/xml",
                        "Accept" :  "application/xml"
                      }
        self.getResponse(authEndPoint, 'POST', userid, passwd, None, reqHeaders=reqHeaders, responseTupple=responseTupple)
        ssoCookie = responseTupple['cookies']['LWSSO_COOKIE_KEY']
        cookieHeader = {
                       "Cookie" : 'LWSSO_COOKIE_KEY='+ssoCookie+';'
                       }
        siteSessionEndPoint = baseEndPoint + '/qcbin/rest/site-session'
        self.getResponse(siteSessionEndPoint, 'POST', None, None, None, reqHeaders=cookieHeader, responseTupple=responseTupple)
        cookieHeader = {
                       "Cookie" : 'LWSSO_COOKIE_KEY='+ssoCookie+';QCSession='+responseTupple['cookies']['QCSession']
                       }
        return cookieHeader
    
    def signOut(self, baseEndPoint):
        signOutEndPoint = baseEndPoint + '/qcbin/authentication-point/logout'
        self.getResponse(signOutEndPoint, 'GET', None, None, None, reqHeaders={})
    
    def getDomains(self, baseEndPoint, cookieHeader):
        projectsEndPoint = baseEndPoint + '/qcbin/rest/domains?include-projects-info=y&alt=application/'+self.responseType.lower()
        projectResponse = self.getResponse(projectsEndPoint, 'GET', None, None, None, reqHeaders=cookieHeader)
        return projectResponse
           
    def getProjectDetails(self, baseEndPoint, reqHeaders, domain, project, entityName, fields, startFrom):
        domainTracking = self.tracking.get(domain, None)
        if domainTracking == None:
            domainTracking = {}
            self.tracking[domain] = domainTracking
        projectTracking = domainTracking.get(project, None)
        if projectTracking == None:
            projectTracking = {}
            domainTracking[project] = projectTracking
        entityTracking = projectTracking.get(entityName, None)
        projectEndPoint = baseEndPoint + '/qcbin/rest/domains/' + domain + '/projects/' + project + '/' + entityName + '?alt=application/'+self.responseType.lower()+'&'+fields
        trackingFieldName = 'last-modified'
        
        if entityName == 'releases':
            trackingFieldName = 'start-date'
        
        if entityTracking == None:
            projectEndPoint += '&query={'+trackingFieldName+'[>"'+startFrom+'"]}&order-by={'+trackingFieldName+'[ASC]}'
        else:
            projectEndPoint += '&query={'+trackingFieldName+'[>"'+entityTracking+'"]}&order-by={'+trackingFieldName+'[ASC]}'
        
        dataList = []
        startIndex = 1
        totalResults = 1
        loadNextPageResult = True
        if self.responseType == 'XML':
            while loadNextPageResult:
                restUrl = projectEndPoint + '&page-size='+str(self.dataFetchCount)+'&start-index='+str(startIndex)
                projectResponse = self.getResponse(restUrl, 'GET', None, None, None, reqHeaders=reqHeaders)
                entities = ET.fromstring(projectResponse)
                totalResults = int(entities.attrib['TotalResults'])
                if totalResults > 0:
                    entities = list(entities.iter('Entity'))
                    for entity in entities:
                        data = {}
                        data['domain'] = domain
                        data['project'] = project
                        data['type'] = entity.attrib['Type']
                        fields = list(entity.iter('Field'))
                        for field in fields:
                            fieldName = field.attrib['Name']
                            fieldValue = self.extractValueWithType(field.find('Value').text)
                            data[fieldName] = fieldValue
                        dataList.append(data)
                startIndex += self.dataFetchCount
                if totalResults < startIndex:
                    loadNextPageResult = False
            if len(dataList) > 0:
                latestRecord = dataList[len(dataList) - 1]
                projectTracking[entityName] = latestRecord[trackingFieldName]
        else:
            while loadNextPageResult:
                restUrl = projectEndPoint + '&page-size='+str(self.dataFetchCount)+'&start-index='+str(startIndex)
                projectResponse = self.getResponse(restUrl, 'GET', None, None, None, reqHeaders=reqHeaders)
                totalResults = projectResponse.get("TotalResults",0)
                if totalResults > 0:
                    entities = projectResponse.get("entities", [])
                    for entity in entities:
                        data = {}
                        data['domain'] = domain
                        data['project'] = project
                        data['type'] = entity['Type']
                        fields = entity['Fields']
                        for field in fields:
                            values = field['values']
                            for value in values:
                                fieldValue = value.get('value', '')
                                data[field['Name']] = fieldValue
                        dataList.append(data)
                startIndex += self.dataFetchCount
                if totalResults < startIndex:
                    loadNextPageResult = False
            if len(dataList) > 0:
                latestRecord = dataList[len(dataList) - 1]
                projectTracking[entityName] = latestRecord[trackingFieldName]
        return dataList
    
    def extractValueWithType(self, value):
        if value is None:
            return ''
        elif value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        try:
            return int(value)
        except ValueError:
            return value
       
    def process(self):
        baseEndPoint = self.config.get('baseEndPoint')
        self.dataFetchCount = self.config.get('dataFetchCount', 200)
        cookieHeader = self.getHpAlmSSOHeader(baseEndPoint)
        domainResponse = self.getDomains(baseEndPoint, cookieHeader)
        startFrom = self.config.get("startFrom", '')
        almEntities = self.config.get("almEntities")
        if almEntities:
            for almEntity in almEntities:
                fieldsList = almEntities[almEntity]
                if len(fieldsList) > 0:
                    fields = 'fields='
                    for field in fieldsList:
                        fields += field + ','
                    if self.responseType == 'XML':
                        tree = ET.fromstring(domainResponse)
                        domains = list(tree.iter('Domain'))
                        for domain in domains:
                            domainName = domain.attrib['Name']
                            projects = list(domain.iter('Project'))
                            for project in projects:
                                projectName = project.attrib['Name']
                                dataList = self.getProjectDetails(baseEndPoint, cookieHeader, domainName, projectName, almEntity, fields, startFrom)
                                if len(dataList) > 0 :
                                    self.publishToolsData(dataList)
                                    self.updateTrackingJson(self.tracking)
                    else:
                        domains = domainResponse.get('Domain')
                        for domain in domains:
                            domainName = domain['Name']
                            projects = domain['Projects']['Project']
                            for project in projects:
                                projectName = project['Name']
                                dataList = self.getProjectDetails(baseEndPoint, cookieHeader, domainName, projectName, almEntity, fields, startFrom)
                                if len(dataList) > 0 :
                                    self.publishToolsData(dataList)
                                    self.updateTrackingJson(self.tracking)
        self.signOut(baseEndPoint)
if __name__ == "__main__":
    HpAlmAgent()        
