/*******************************************************************************
 * Copyright 2017 Cognizant Technology Solutions
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
package com.cognizant.devops.platformregressiontest.test.ui.reportmanagement;

import org.testng.Assert;
import org.testng.annotations.AfterTest;
import org.testng.annotations.BeforeTest;
import org.testng.annotations.Test;

import com.cognizant.devops.platformregressiontest.test.common.ConfigOptionsTest;
import com.cognizant.devops.platformregressiontest.test.common.LoginAndSelectModule;

public class ReportManagementTest extends LoginAndSelectModule {

	AssessmentReportConfiguration clickAllButton;

	@BeforeTest
	public void setUp() {
		initialization();
		getData(ConfigOptionsTest.REPORT_JSON_FILE);
		selectMenuOption(LoginAndSelectModule.testData.get("reportManagement"));		
		clickAllButton = new AssessmentReportConfiguration();
	}

	@Test(priority = 1)
	public void addReport() {

		Assert.assertTrue(clickAllButton.addNewReport(), "Not able to add Report");
		Assert.assertTrue(clickAllButton.navigateToReportsLandingPage(),
				"Not able to navigate to reports landing page");
	}

	@Test(priority = 2)
	public void duplicateRecordError() {

		Assert.assertTrue(clickAllButton.navigateToReportsLandingPage(), "ReportName already exists");

	}

	@Test(priority = 3)
	public void updateReport() throws InterruptedException {

		Assert.assertTrue(clickAllButton.editReport(), "Not able to navigate to landing page");

	}

	@Test(priority = 4)
	public void inActiveReport() throws InterruptedException {

		Assert.assertTrue(clickAllButton.inActiveReport(), "Not able to navigate to reports landing page");

	}

	@Test(priority = 5)
	public void deleteReport() {
		Assert.assertTrue(clickAllButton.deleteReport(), "Not able to delete the report");
	}

	@AfterTest
	public void tearDown() {

		driver.quit();
	}

}