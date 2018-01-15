package com.cognizant.devops.platforminsights.core.count;

import static org.junit.Assert.*;

import java.util.HashMap;
import java.util.Map;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.MockitoJUnit;
import org.mockito.junit.MockitoRule;

import com.cognizant.devops.platformcommons.config.ApplicationConfigCache;
import com.cognizant.devops.platforminsights.configs.ConfigConstants;

public class CountActionImplTest {
	@Mock
	CountActionImpl countImpl;
	
	@Rule
	public MockitoRule rule = MockitoJUnit.rule();
	
	@Before
	public void load(){
	ApplicationConfigCache.loadConfigCache();
	}
	
	@Test
	public void testExecute() {
		load();
		assertEquals("9200", ConfigConstants.SPARK_ES_PORT);
		
		Map<String, Object> resultMap = new HashMap<String, Object>();
		resultMap.put("Jobs", "Success");
		
		//When there are some jobs
		Mockito.when(countImpl.execute()).thenReturn(resultMap);
		assertEquals(resultMap.get("Jobs"),countImpl.execute().get("Jobs"));
		
		//When no jobs are present
		Mockito.when(countImpl.execute()).thenReturn(null);
		assertNull(countImpl.execute());
	}

}
