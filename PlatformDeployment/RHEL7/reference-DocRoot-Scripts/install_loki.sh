#-------------------------------------------------------------------------------
# Copyright 2020 Cognizant Technology Solutions
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
# Install Loki
echo "#################### Installing Loki ####################"
source /etc/environment
source /etc/profile
cd $INSIGHTS_APP_ROOT_DIRECTORY
sudo mkdir Loki
cd Loki
read -p "Please enter Loki version number you want to install(ex. 2.4.2 or 2.5.0): " version_number
sudo wget https://github.com/grafana/loki/releases/download/v${version_number}/loki-linux-amd64.zip
sudo unzip "loki-linux-amd64.zip"
sudo rm -r -f loki-linux-amd64.zip
sudo chmod a+x "loki-linux-amd64"
#sudo ./loki-linux-amd64 -config.file=loki-local-config.yaml
export LOKI_HOME=`pwd`
sudo echo LOKI_HOME=`pwd` | sudo tee -a /etc/environment
sudo echo "export" LOKI_HOME=`pwd` | sudo tee -a /etc/profile
cd /etc/init.d/
sudo wget https://raw.githubusercontent.com/CognizantOneDevOps/Insights/master/PlatformDeployment/RHEL7/initscripts/InsightsLoki.sh
sudo mv InsightsLoki.sh InsightsLoki
sudo chmod +x InsightsLoki
sudo chkconfig InsightsLoki on
sudo yum install dos2unix
sudo dos2unix /etc/init.d/InsightsLoki
sudo service InsightsLoki stop
sleep 5
sudo service InsightsLoki start
sleep 5
echo "#################### Loki is up ####################"
echo "#################### Installation Completed ####################"

