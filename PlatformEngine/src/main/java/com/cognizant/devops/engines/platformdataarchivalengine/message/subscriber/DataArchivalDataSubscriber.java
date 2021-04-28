/*******************************************************************************
 * Copyright 2020 Cognizant Technology Solutions
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License.  You may obtain a copy
 * of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations under
 * the License.
 ******************************************************************************/

package com.cognizant.devops.engines.platformdataarchivalengine.message.subscriber;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import javax.persistence.NoResultException;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import com.cognizant.devops.engines.platformengine.message.factory.EngineSubscriberResponseHandler;
import com.cognizant.devops.platformcommons.constants.DataArchivalConstants;
import com.cognizant.devops.platformcommons.constants.MQMessageConstants;
import com.cognizant.devops.platformcommons.constants.PlatformServiceConstants;
import com.cognizant.devops.platformcommons.core.enums.DataArchivalStatus;
import com.cognizant.devops.platformcommons.core.util.InsightsUtils;
import com.cognizant.devops.platformcommons.exception.InsightsCustomException;
import com.cognizant.devops.platformdal.dataArchivalConfig.DataArchivalConfigDal;
import com.cognizant.devops.platformdal.dataArchivalConfig.InsightsDataArchivalConfig;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.rabbitmq.client.AMQP.BasicProperties;
import com.rabbitmq.client.Envelope;

public class DataArchivalDataSubscriber extends EngineSubscriberResponseHandler {

	private static Logger log = LogManager.getLogger(DataArchivalDataSubscriber.class);
	DataArchivalConfigDal dataArchivalConfigDAL = new DataArchivalConfigDal();
	JsonParser parser = new JsonParser();

	public DataArchivalDataSubscriber(String routingKey) throws Exception {
		super(routingKey);
	}

	@Override
	public void handleDelivery(String consumerTag, Envelope envelope, BasicProperties properties, byte[] body)
			throws IOException {
		String message=null;
		try {
			message = new String(body, MQMessageConstants.MESSAGE_ENCODING);
			JsonArray messageJson = parser.parse(message).getAsJsonObject().get("data").getAsJsonArray();
			JsonObject updateURLJson = messageJson.get(0).getAsJsonObject();
			if (PlatformServiceConstants.SUCCESS.equalsIgnoreCase(updateURLJson.get("status").getAsString())) {
				String containerID = updateURLJson.get(DataArchivalConstants.CONTAINERID).getAsString();
				if (containerID.isEmpty()) {
					throw new InsightsCustomException("ContainerID not present in message");
				}
				if(updateURLJson.has(DataArchivalConstants.TASK) && "remove_container".equalsIgnoreCase(updateURLJson.get(DataArchivalConstants.TASK).getAsString())) {
					InsightsDataArchivalConfig archivalConfigs = dataArchivalConfigDAL.getArchivalRecordByContainerId(containerID);
					dataArchivalConfigDAL.updateArchivalStatus(archivalConfigs.getArchivalName(), DataArchivalStatus.TERMINATED.toString());
				} else {
					String archivalName = updateURLJson.get(DataArchivalConstants.ARCHIVALNAME).getAsString();
					String sourceUrl = updateURLJson.get(DataArchivalConstants.SOURCEURL).getAsString();
					int boltPort = updateURLJson.get(DataArchivalConstants.BOLTPORT).getAsInt();
					Long expiryDate = getExpiryDate(archivalName);
					log.debug("Inside Data archival data:- archivalName: {} , sourceUrl: {} ", archivalName, sourceUrl);
					if (archivalName.isEmpty()) {
						throw new InsightsCustomException("Archival name not present in message");
					} else if (sourceUrl.isEmpty()) {
						throw new InsightsCustomException("Container URL not present in message");
					}
					dataArchivalConfigDAL.updateContainerDetails(archivalName, sourceUrl, containerID, expiryDate,boltPort);
				}
				getChannel().basicAck(envelope.getDeliveryTag(), false);
			} else {
				getChannel().basicAck(envelope.getDeliveryTag(), false);
				throw new InsightsCustomException("Failed status in Data archival message received from MQ.");
			}
		} catch (NoResultException e) {
			log.error("No Record found occured ", e);
			log.error(" data message :{} ",message);
			getChannel().basicAck(envelope.getDeliveryTag(), false);
		} catch (Exception e) {
			log.error("Exception occured ", e);
		}

	}

	private Long getExpiryDate(String archivalName) {
		InsightsDataArchivalConfig config = dataArchivalConfigDAL.getSpecificArchivalRecord(archivalName);
		Long daysInMillis = TimeUnit.DAYS.toMillis(config.getDaysToRetain());
		return ((InsightsUtils.getTodayTime() + daysInMillis)/1000);
	}

}
