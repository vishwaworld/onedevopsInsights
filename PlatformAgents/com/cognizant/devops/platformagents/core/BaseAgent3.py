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
Created on Jun 16, 2016

@author: 146414
'''

import json
import requests
from .MessageQueueProvider3 import MessageFactory
from .CommunicationFacade3 import CommunicationFacade
from apscheduler.schedulers.blocking import BlockingScheduler
import sys
import os.path
import uuid
from datetime import datetime
from pytz import timezone
import logging.handlers
import time

class BaseAgent(object):
       
    def __init__(self):
        try:
            self.shouldAgentRun = True;
            self.setupAgent()
        except Exception as ex:
            logging.error(ex)
            self.publishHealthData(self.generateHealthData(ex=ex))
            self.logIndicator(self.SETUP_ERROR, self.config.get('isDebugAllowed', False))

    def setupAgent(self):
        self.resolveConfigPath()
        self.loadConfig()
        self.fetchAgentCredentials()
        self.setupLogging()
        self.loadTrackingConfig()
        self.loadCommunicationFacade()
        self.initializeMQ()
        #self.configUpdateSubscriber()
        self.subscriberForAgentControl()
        self.setupLocalCache()
        self.extractToolName()
        self.scheduleExtensions()
        self.execute()
        self.scheduleAgent()

    def fetchAgentCredentials(self):
        self.vaultFlag = self.config.get("vault").get("getFromVault", False)
        if self.vaultFlag:
            VaultCredentials = self.loadVaultCredentials()
            self.vaultJson = VaultCredentials.json()
            if "errors" in self.vaultJson:
                self.publishHealthData(self.generateHealthData(systemFailure=True,note="BaseAgent: unable to fetchCredentials from vault"))
                raise ValueError('BaseAgent: unable to fetchCredentials from vault')
    
    def getCredential(self,key):
        if self.vaultFlag:
            return self.vaultJson["data"]["data"][key]
        else: 
            return self.config.get(key, None)

    def loadVaultCredentials(self):
        agentId=self.config.get("agentId", '')
        readTokenValue=self.config.get("vault").get("readToken", '')
        secretEngine=self.config.get("vault").get("secretEngine", '')
        vaultUrl=self.config.get("vault").get("vaultUrl", '')
        reqHeaders = {'Accept':'application/json','X-Vault-Token':readTokenValue}
        agentCredential = requests.get(vaultUrl+secretEngine+"/data/"+agentId, auth=None, headers=reqHeaders, data=None,proxies=None, verify=None)
        # agentCredential=os.popen("curl -X GET -H 'X-Vault-Token: "+readTokenValue+"\'"+" -s "+vaultUrl+secretEngine+"/data/"+agentId).read()
        if "errors" in agentCredential:
            self.publishHealthData(self.generateHealthData(systemFailure=True,note="BaseAgent: unable to load Vault Credentials"))
            raise ValueError(' BaseAgent: unable to load Vault Credentials ')
        return agentCredential
        
    
    def resolveConfigPath(self):
        filePresent = os.path.isfile('config.json')
        agentDir = os.path.dirname(sys.modules[self.__class__.__module__].__file__) + os.path.sep
        if "INSIGHTS_HOME" in os.environ:
            logDirPath = os.environ['INSIGHTS_HOME']+'/logs/PlatformAgent'
            if not os.path.exists(logDirPath):
                os.makedirs(logDirPath)
        else:
            logDirPath = agentDir
        if filePresent:
            self.configFilePath = 'config.json'
            self.trackingFilePath = 'tracking.json'
            #self.logFilePath = logDirPath +'/'+ 'log_'+type(self).__name__+'.log'            
        else:
            self.configFilePath = agentDir+'config.json'
            self.trackingFilePath = agentDir+'tracking.json' 
	    #self.logFilePath = logDirPath + '/'+'log_'+type(self).__name__+'.log'	    
        trackingFilePresent = os.path.isfile(self.trackingFilePath)
        if not trackingFilePresent:
            self.updateTrackingJson({})
    
    def setupLogging(self):
        agentDir = os.path.dirname(sys.modules[self.__class__.__module__].__file__) + os.path.sep
        self.logFilePath = agentDir +'/'+ 'log_'+type(self).__name__+'.log'
        if self.config.get('agentId') != None and self.config.get('agentId') != '':
            if "INSIGHTS_HOME" in os.environ:
                logDirPath = os.environ['INSIGHTS_HOME']+'/logs/PlatformAgent'
                if not os.path.exists(logDirPath):
                    os.makedirs(logDirPath)
                self.logFilePath = logDirPath +'/'+ 'log_'+self.config.get('agentId')+'.log'
        
        loggingSetting = self.config.get('loggingSetting',{})
        maxBytes = loggingSetting.get('maxBytes', 1000 * 1000 * 5)
        backupCount = loggingSetting.get('backupCount', 1000)
        handler = logging.handlers.RotatingFileHandler(self.logFilePath, maxBytes=maxBytes, backupCount=backupCount)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(lineno)s - %(funcName)s - %(message)s')
        handler.setFormatter(formatter)
        logging.getLogger().setLevel(loggingSetting.get('logLevel',logging.WARN))
        logging.getLogger("pika").setLevel(logging.WARNING)
        logging.getLogger().addHandler(handler)
    
    def setupLocalCache(self):
        self.dataRoutingKey = str(self.config.get('publish').get('data'))
        self.healthRoutingKey = str(self.config.get('publish').get('health'))
        self.runSchedule = self.config.get('runSchedule', 30)
        self.insightsTimeZone = timezone('UTC')
        self.toolsTimeZone = timezone(self.config.get('toolsTimeZone'))
        self.epochStartDateTime = datetime(1970, 1, 1, tzinfo=self.insightsTimeZone)
        isEpochTime = self.config.get('isEpochTimeFormat', False)
        if not isEpochTime:
            self.dateTimeLength = len(self.epochStartDateTime.strftime(self.config.get('timeStampFormat', None)))
        self.buildTimeFormatLengthMapping()      
    
    def buildTimeFormatLengthMapping(self):
        self.timeFormatLengthMapping = {}
        timeFieldMapping = self.config.get('dynamicTemplate', {}).get('timeFieldMapping', None)
        if timeFieldMapping:
            for field in timeFieldMapping:
                self.timeFormatLengthMapping[field] = len(self.epochStartDateTime.strftime(timeFieldMapping[field]))
        
    
    def extractToolName(self):
        tokens = self.dataRoutingKey.split('.')
        self.categoryName = tokens[0]
        self.toolName = tokens[1]
        self.categoryName = self.config.get('toolCategory', tokens[0])      
        self.toolName = self.config.get('toolName', tokens[1])
         
    
    def loadConfig(self):
        with open(self.configFilePath, 'r') as config_file:    
            self.config = json.load(config_file)
        if self.config == None:
            raise ValueError('BaseAgent: unable to load config JSON')
        
    def loadTrackingConfig(self):
        with open(self.trackingFilePath, 'r') as config_file:    
            self.tracking = json.load(config_file)
        if self.tracking == None:
            raise ValueError('BaseAgent: unable to load tracking JSON')
        
    def loadCommunicationFacade(self):
        communicationFacade = CommunicationFacade();
        config = self.config.get('communication',{})
        facadeType = config.get('type', None)
        sslVerify = config.get('sslVerify', True)
        self.responseType = config.get('responseType', 'JSON')
        enableValueArray = self.config.get('enableValueArray', False)
        self.communicationFacade = communicationFacade.getCommunicationFacade(facadeType, sslVerify, self.responseType, enableValueArray)
        
    def initializeMQ(self):
        mqConfig = self.config.get('mqConfig', None)
        if mqConfig == None:
            raise ValueError('BaseAgent: unable to initialize MQ. mqConfig is not found')
        
        user = mqConfig.get('user', None)
        mqPass =  mqConfig.get('password', None)
        host = mqConfig.get('host', None)
        exchange = mqConfig.get('exchange', None)
        agentCtrlXchg  = mqConfig.get('agentControlXchg', None)
        
        self.messageFactory = MessageFactory(user,mqPass,host,exchange)
        if self.messageFactory == None:
            raise ValueError('BaseAgent: unable to initialize MQ. messageFactory is Null')
        
        self.agentCtrlMessageFactory = MessageFactory(user,mqPass,host,agentCtrlXchg)

    '''
    Subscribe for Agent START/STOP exchange and queue
    '''
    def subscriberForAgentControl(self):
        routingKey = self.config.get('subscribe').get('agentCtrlQueue')
        def callback(ch, method, properties, data):
            logging.debug("Data received in subscriberForAgentControl .... ")
            logging.debug(data)
            #Update the config file and cache.
            action = data
            if "STOP" == action.decode():
                self.shouldAgentRun = False
            ch.basic_ack(delivery_tag = method.delivery_tag)
            logging.debug(self.shouldAgentRun)
        self.agentCtrlMessageFactory.subscribe(routingKey, callback)
           
    '''
    Subscribe for Engine Config Changes. Any changes to respective agent will be consumed and processed here.
    '''
    def configUpdateSubscriber(self):
        routingKey = self.config.get('subscribe').get('config')
        def callback(ch, method, properties, data):
            #Update the config file and cache.
            updatedConfig = json.loads(data)
            self.updateJsonFile(self.configFilePath, updatedConfig)
            self.config = updatedConfig 
            self.setupLocalCache()
            ch.basic_ack(delivery_tag = method.delivery_tag)
        self.messageFactory.subscribe(routingKey, callback)
                
    '''
        Supported metadata attributes:
        {
            labels : [] --> Array of additional labels to applied to data
            dataUpdateSupported: true/false --> if the existing data node is supposed to be updated
            uniqeKey: String --> comma separated node properties
        }
    '''
    def publishToolsData(self, data, metadata=None, auditing=False, timeStampField=None, timeStampFormat=None, isEpochTime=False,isExtension=False):
        if metadata:
            metadataType = type(metadata)
            if metadataType is not dict:
                raise ValueError('BaseAgent: Dict metadata object is expected')
        if data:
            enableDataValidation = self.config.get('enableDataValidation',False)
            if enableDataValidation:
                data = self.validateData(data)
            self.addExecutionId(data, self.executionId)
            self.addTimeStampField(data, timeStampField, timeStampFormat, isEpochTime,isExtension)
            logging.info(data)
            if auditing:
                self.addDigitalSign(data)
            self.messageFactory.publish(self.dataRoutingKey, data, self.config.get('dataBatchSize', 100), metadata)
            self.logIndicator(self.PUBLISH_START, self.config.get('isDebugAllowed', False))
            
    '''
        This method validates data and 
        removes any JSON which contains nested JSON object 
        as an element value
    '''
    def validateData(self, data):   
        corrected_json_array =[]
        showErrorMessage = False
        for each_json in data:    
            errorFlag = False
            for element in each_json:        
                if isinstance(each_json[element],dict):
                    errorFlag = True
                    showErrorMessage = True
                    logging.error('Value is not in expected format, nested JSON encountered.Rejecting: '+ str(each_json))                    
                    break;
            if not errorFlag:
                corrected_json_array.append(each_json)
        if showErrorMessage:
            self.publishHealthData(self.generateHealthData(note="Agent has encountered nested JSON, rejecting that node."))     
        data = []
        data = corrected_json_array
        return data
        
    def publishHealthData(self, data):
        self.addExecutionId(data, self.executionId)
        self.messageFactory.publish(self.healthRoutingKey, data)
    
    def addTimeStampField(self, data, timeStampField=None, timeStampFormat=None, isEpochTime=False,isExtension=False):
        if timeStampField is None:
            timeStampField = self.config.get('timeStampField')
        if timeStampFormat is None:
            timeStampFormat = self.config.get('timeStampFormat')
        if not isEpochTime and not isExtension:
            isEpochTime = self.config.get('isEpochTimeFormat', False)
        timeFieldMapping = self.config.get('dynamicTemplate', {}).get('timeFieldMapping', None)
        for d in data:
            eventTime = d.get(timeStampField, None)
            if eventTime != None:
                timeResponse = None
                if isEpochTime:
                    eventTime = str(eventTime)
                    eventTime = int(eventTime[:10])
                    timeResponse = self.getRemoteDateTime(datetime.fromtimestamp(eventTime))
                else:
                    eventTime = eventTime[:self.dateTimeLength]
                    timeResponse = self.getRemoteDateTime(datetime.strptime(eventTime, timeStampFormat))
                d['inSightsTime'] = timeResponse['epochTime']
                d['inSightsTimeX'] = timeResponse['time']
            
            if timeFieldMapping:
                for field in timeFieldMapping:
                    timeFormat = timeFieldMapping[field]
                    outputField = field + 'Epoch'
                    value = d.get(field, None)
                    if value:
                        try:
                            value = value[:self.timeFormatLengthMapping[field]]
                            d[outputField] = self.getRemoteDateTime(datetime.strptime(value, timeFormat)).get('epochTime')
                        except Exception as ex:
                            logging.warn('Unable to parse timestamp field '+ field)
                            logging.error(ex)
            
            d['toolName'] = self.toolName;
            d['categoryName'] = self.categoryName; 
                        
    def getRemoteDateTime(self, time):
        localDateTime = self.toolsTimeZone.localize(time)
        remoteDateTime = localDateTime.astimezone(self.insightsTimeZone)
        response = {
                    'epochTime' : (remoteDateTime - self.epochStartDateTime).total_seconds(),
                    'time' : remoteDateTime.strftime('%Y-%m-%dT%H:%M:%SZ')
                    }
        return response;
    
    def addExecutionId(self, data, executionId):
        for d in data:
            d['execId'] = executionId
			
    def addDigitalSign(self, data):
        dataString = ''
        for d in data:
            for key in sorted(d.keys()):
                if(key !="digitalSignature" and d[key]!= None):
                    #print(key,"--->",d[key])
                    if type(d[key])== str:
                        dataString += d[key]
                    elif type(d[key])==list:
                        for each in d[key]:
                            dataString += str(each)
                    elif type(d[key]) == bool:
                        dataString += str(d[key]).lower()
                    else:
                        dataString += str(d[key])
            #print("dataString")
            #print(dataString)
            hex = hashlib.sha256(dataString.encode('utf-8')).hexdigest()
            #print(hex)
            hex_signature = self.rsaEncrypt(hex)
			
            d['digitalSignature'] = hex_signature.decode('utf-8')
            #print(d['digitalSignature'])
            dataString = ''
    
    def rsaEncrypt(self, hexdigest):
        #print("+++++++++++++++++++++++++++++++++hexdigest")
        #print(hexdigest)
        with open(self.config.get('publicKeyPath'), 'rb') as key_file:
            public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )
        encrypted = public_key.encrypt(
        hexdigest.encode('utf-8'),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA256(),
            label=None
        ))
        return b64encode(encrypted)
    
    def updateTrackingJson(self, data):
        #Update the tracking json file and cache.
        self.updateJsonFile(self.trackingFilePath, data)
            
    def updateJsonFile(self, jsonFile, data):
        with open(jsonFile, 'w') as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)
        
    def getResponse(self, url, method, userName, password, data, authType='BASIC', reqHeaders=None, responseTupple=None,proxies=None):
        return self.communicationFacade.communicate(url, method, userName, password, data, authType, reqHeaders, responseTupple,proxies)        
   
    def parseResponse(self, template, response, injectData={}):
        return self.communicationFacade.processResponse(template, response, injectData, self.config.get('useResponseTemplate',False))
    
    def getResponseTemplate(self):
        return self.config.get('dynamicTemplate', {}).get('responseTemplate',None)
    
    def generateHealthData(self, ex=None, systemFailure=False,note=None, additionalProperties=None):
        data = []
        currentTime = self.getRemoteDateTime(datetime.utcnow())
        tokens = self.dataRoutingKey.split('.')
        self.categoryName = tokens[0]
        self.toolName = tokens[1]
        health_basic = { 'toolName' : self.config.get('toolName', tokens[1]), 'categoryName' : self.config.get('toolCategory', tokens[0]), 'agentId' : self.config.get('agentId'), 'inSightsTimeX' : currentTime['time'], 'inSightsTime' : currentTime['epochTime'], 'executionTime' : int((datetime.now() - self.executionStartTime).total_seconds() * 1000)}
        if additionalProperties != None:
            data_json = {key: value for (key, value) in (health_basic.items() + additionalProperties.items())}
            health_basic_str = json.dumps(data_json)
            health = json.loads(health_basic_str)
        else:
            health = health_basic 
        if systemFailure:
            health['status'] = 'failure'
            health['message'] = 'Agent is shutting down'
        elif ex != None:
            health['status'] = 'failure'
            health['message'] = 'Error occurred: '+str(ex)
            logging.error(ex)
        else:
            health['status'] = 'success'
            if note != None:
                health['message'] = note
        data.append(health)
        logging.debug(data)
        return data
    
    def scheduleAgent(self):
        if not hasattr(self, 'scheduler'):
            scheduler = BlockingScheduler()
            self.scheduler = scheduler
            self.scheduledJob = scheduler.add_job(self.execute,'interval', seconds=60*self.runSchedule)
            try:
                scheduler.start()
            except (KeyboardInterrupt, SystemExit):
                self.publishHealthData(self.generateHealthData(systemFailure=True))
                
        else:
            scheduler = self.scheduler
            schedulerStatus = self.config.get('schedulerStatus', None)
            if schedulerStatus == 'UPDATE_SCHEDULE':
                self.scheduledJob.reschedule('interval', seconds=60*self.runSchedule)
            elif schedulerStatus == 'STOP':
                scheduler.shutdown()
            elif schedulerStatus == 'PAUSE':
                scheduler.pause()
            elif schedulerStatus == 'RESUME':
                scheduler.resume()
            elif schedulerStatus == 'RESTART':
                scheduler.start()
            else:
                pass
    
    def scheduleExtensions(self):
        '''
        Schedule the extensions from here
        '''
    '''
    Register the agent extensions. All the extensions will be called after the time interval specified using duration (in minutes)
    '''
    def registerExtension(self, name, func, duration):
        if not hasattr(self, 'extensions'):
            self.extensions = {}
        self.extensions[name] = {'func': func, 'duration': duration}
    
    def execute(self):
        logging.debug('Agent is in START mode')
        try:
            self.executionStartTime = datetime.now()
            self.logIndicator(self.EXECUTION_START, self.config.get('isDebugAllowed', False))
            self.executionId = str(uuid.uuid1())
            self.process()
            self.executeAgentExtensions()
            self.publishHealthData(self.generateHealthData(note="Agent started successfully "))
        except Exception as ex:
            self.publishHealthDataForExceptions(ex)
        finally:
            '''If agent receive the STOP command, Python program should exit gracefully after current data collection is complete.  '''
            if self.shouldAgentRun == False:
                logging.debug('executing agent stop and publish health message health message  ....   ')
                try:
                    self.publishHealthData(self.generateHealthData(note="Agent is in STOP mode"))
                    os._exit(0)
                except Exception as ex:
                    logging.error(ex)

    '''
        This method publishes health node for an exception and 
        Writes exception inside log file of corresponding Agent 
    '''
    def publishHealthDataForExceptions(self, ex):
        logging.error(ex)
        self.publishHealthData(self.generateHealthData(ex=ex))
        self.logIndicator(self.EXECUTION_ERROR, self.config.get('isDebugAllowed', False))
    
    def executeAgentExtensions(self):
        if hasattr(self, 'extensions'):
            extensions = self.extensions
            agentExtensionsTracking = self.tracking.get('agentExtensions', None)
            if agentExtensionsTracking is None:
                agentExtensionsTracking = {}
                self.tracking['agentExtensions'] = agentExtensionsTracking
            for name in extensions:
                extension = extensions[name]
                duration = extension.get('duration') * 60
                lastRunTime = agentExtensionsTracking.get(name, None)
                executeExtension = False
                if lastRunTime is None:
                    executeExtension = True
                else:
                    currentEpochTime = self.getRemoteDateTime(datetime.now()).get('epochTime')
                    lastRunEpochTime = self.getRemoteDateTime(datetime.strptime(lastRunTime, '%Y-%m-%d %H:%M:%S')).get('epochTime')
                    if currentEpochTime >= (lastRunEpochTime + duration):
                        executeExtension = True
                    else:
                        executeExtension = False
                if executeExtension:
                    func = extension.get('func')
                    func()
                    agentExtensionsTracking[name] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
                    self.updateTrackingJson(self.tracking)
                    
        
    def process(self):
        '''
        Override process in Agent class
        '''
    
    EXECUTION_START = 1
    PUBLISH_START = 2
    EXECUTION_ERROR = 3
    SETUP_ERROR = 4
    
    def logIndicator(self, indicator, isDebugAllowed=False):
        if isDebugAllowed:
            if indicator == self.EXECUTION_START :
                sys.stdout.write('.')
            elif indicator == self.PUBLISH_START :
                sys.stdout.write('*')
            elif indicator == self.EXECUTION_ERROR :
                sys.stdout.write('|')
            elif indicator == self.SETUP_ERROR :
                sys.stdout.write('#')
