Inital main release for cucm_service_do.py

The script performs a specified action on a list of Cisco CUCM servers.

Uses AXL SOAP API with Cisco Control Center Services wsdl to perform actions. 
(https://developer.cisco.com/docs/sxml/#control-center-services-api-reference).
Code assumes ControlCenterServices.wsdl is in working python folder.

Create ucmlist.txt in same folder as application to drive CUCM selection.
It contains simple list of UCM IP addresses or FQDNs.  See included example.

Execute the script with no command line parameters to display help text:
Syntax:
cucm_service_do.py axl_username axl_password (in Single quotes), UCM Service Name (in Single quotes), Action (Start,Stop,Restart)

The default Action is Restart.

This release uses basic authentication.  If required, uncomment appropriate lines to
enable certificate checking.


