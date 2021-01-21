/*******************************************************************************
 *  * Copyright 2017 Cognizant Technology Solutions
 *  * 
 *  * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 *  * use this file except in compliance with the License.  You may obtain a copy
 *  * of the License at
 *  * 
 *  *   http://www.apache.org/licenses/LICENSE-2.0
 *  * 
 *  * Unless required by applicable law or agreed to in writing, software
 *  * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 *  * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 *  * License for the specific language governing permissions and limitations under
 *  * the License.
 *******************************************************************************/
package com.cognizant.devops.platformreports.test.testngInitializer;

import java.lang.annotation.Annotation;
import java.lang.reflect.Field;
import java.lang.reflect.Proxy;
import java.util.HashMap;
import java.util.Map;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.testng.annotations.BeforeSuite;
import org.testng.annotations.Test;

import com.cognizant.devops.platformcommons.config.ApplicationConfigCache;
import com.cognizant.devops.platformcommons.config.ApplicationConfigProvider;
import com.cognizant.devops.platformcommons.constants.UnitTestConstant;
import com.cognizant.devops.platformcommons.exception.InsightsCustomException;
import com.cognizant.devops.platformdal.assessmentreport.InsightsReportTemplateConfigFiles;
import com.cognizant.devops.platformdal.assessmentreport.InsightsReportVisualizationContainer;
import com.cognizant.devops.platformdal.filemanagement.InsightsConfigFiles;

@Test
public class TestngInitializerTest{
	
	static Logger log = LogManager.getLogger(TestngInitializerTest.class);

	@BeforeSuite
	public void testOnStartup() throws Exception {
		try {
			ApplicationConfigCache.loadConfigCache();
			changeAnnotationValue();
			loadDBDetails();
		} catch (InsightsCustomException e) {
			log.error(e);
		}
		log.debug("Testng initializer class to load Config Cache");
	}
	
	public void loadDBDetails() {
		ApplicationConfigProvider.getInstance().getPostgre().setInsightsDBUrl(UnitTestConstant.H2_DB_URL);
		ApplicationConfigProvider.getInstance().getPostgre().setDriver(UnitTestConstant.H2_DRIVER);
		ApplicationConfigProvider.getInstance().getPostgre().setDialect(UnitTestConstant.H2_DIALECT);
		ApplicationConfigProvider.updateConfig(ApplicationConfigProvider.getInstance());
	}
	
	public void changeAnnotationValue() throws NoSuchFieldException, SecurityException, ClassNotFoundException {
		Map<Object,String> classMap = new HashMap<>();
		classMap.put(new InsightsConfigFiles(),"fileData");
		classMap.put(new InsightsReportTemplateConfigFiles(),"fileData");
		classMap.put(new InsightsReportVisualizationContainer(),"attachmentData");
		for(Map.Entry<Object, String> entry : classMap.entrySet()) {
		Field field = entry.getKey().getClass().getDeclaredField(entry.getValue());
		Annotation annotations = field.getAnnotations()[0];
		Object handler = Proxy.getInvocationHandler(annotations);
		System.out.println("Field : "+ field.getName());
		field.setAccessible(true);
        Field f;
        try {
            f = handler.getClass().getDeclaredField("memberValues");
        } catch (NoSuchFieldException | SecurityException e) {
            throw new IllegalStateException(e);
        }
        f.setAccessible(true);
        Map<String, Object> memberValues;
        try {
            memberValues = (Map<String, Object>) f.get(handler);
        } catch (IllegalArgumentException | IllegalAccessException e) {
            throw new IllegalStateException(e);
        }
        Object oldValue = memberValues.get("columnDefinition");
        memberValues.put("columnDefinition","BLOB");
		}
	}
}
