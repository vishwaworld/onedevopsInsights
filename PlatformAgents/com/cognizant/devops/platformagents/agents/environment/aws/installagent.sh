# Turn on a case-insensitive matching (-s set nocasematch)
opt=$1
action=$2
echo "$opt"
case $opt in
        [lL][Ii][nN][uU][Xx])
          case $action in 
            [uU][nN][iI][nN][sS][tT][aA][lL][lL])
	          	sudo service InSightsAwsAgent stop
				sudo rm -R /etc/init.d/InSightsAwsAgent
				echo "Service un-installation step completed"
		        ;;
		    *)
                echo "Aws Running on Linux..."
				sudo cp -xp InSightsAwsAgent.sh  /etc/init.d/InSightsAwsAgent
				sudo chmod +x /etc/init.d/InSightsAwsAgent
				sudo chkconfig InSightsAwsAgent on
				sudo service  InSightsAwsAgent status
				sudo service  InSightsAwsAgent stop
				sudo service  InSightsAwsAgent status
				sudo service  InSightsAwsAgent start
				sudo service  InSightsAwsAgent status
				
				echo "Service installaton steps completed"
                ;;
		  esac
		  ;;
        [uU][bB][uU][nN][tT][uU])
	       case $action in 
             [uU][nN][iI][nN][sS][tT][aA][lL][lL]) 
				sudo systemctl stop InSightsAwsAgent
				sudo rm -R /etc/systemd/system/InSightsAwsAgent.service
				echo "Service un-installation step completed"				
			    ;;
			 *)
                echo "Aws Running on Ubuntu..."
				sudo cp -xp InSightsAwsAgent.service /etc/systemd/system
				sudo systemctl enable InSightsAwsAgent
				sudo systemctl start InSightsAwsAgent
				echo "Service installaton steps completed"
                ;;
		   esac
		   ;;
        centos)
                echo "Aws Running on centso..."
                ;;
        *)
        	    echo "Please provide correct OS input"
esac