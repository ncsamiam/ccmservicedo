"""Serviceability Control Center Services <doControlServices> script
Performs a <soapDoControlServices> request using the Zeep SOAP library,
periodically checks the status using <soapGetServiceStatus> and parses/prints
the results in a simple table output.
Copyright (c) 2021 Cisco and/or its affiliates.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import time
from lxml import etree
import requests
from requests import Session
from requests.auth import HTTPBasicAuth

from zeep import Client, Settings, Plugin
from zeep.transports import Transport
from zeep.exceptions import Fault

import os
import sys
import time

# Escape codes for terminal text colors
class bcolors:
    RESET = '\033[39m'
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLDON = '\033[1m'
    UNDERLINE = '\033[4m'
    BOLDOFF = '\033[2m'

# get and validate CLI parameters

if len(sys.argv)<3:
    sys.exit(bcolors.HEADER+'\n-- Syntax --\n\n'+bcolors.OKGREEN+'cucm_service_do.py axl_username axl_password (in Single quotes), UCM Service Name (in Single quotes), Action (Start,Stop,Restart)'+bcolors.RESET+'\nIf no action is specified the default is Restart\n\nExample: '+bcolors.HEADER+bcolors.BOLDON+'cucm_service_do.py admin \'Cisc0123\' \'Cisco Tftp\' Restart\n\n'+bcolors.RESET+'Note that if the case-sensitive Service Name specified is not valid the status will always show "Stopped"\n'+bcolors.HEADER+'-----------\n')

# Set AXL credentials

AXL_USERNAME = str(sys.argv[1])
#Comment Out for Production
#AXL_PASSWORD = "C!sc0123"
#Un-Comment for Production
AXL_PASSWORD = str(sys.argv[2])

# Get Service Name 
SVC_NAME = str(sys.argv[3])

#Is Action valid?  If thrid argument not passed, default is Restart
try:
    SVC_ACTION = str(sys.argv[4])
except:
    SVC_ACTION = "Restart"

if (SVC_ACTION =="Stop" or SVC_ACTION == "stop" or SVC_ACTION == "STOP"):
   SVC_ACTION = "Stop"
elif (SVC_ACTION =="Start" or SVC_ACTION == "start" or SVC_ACTION == "START"):
    SVC_ACTION = "Start"
elif (SVC_ACTION =="Restart" or SVC_ACTION == "restart" or SVC_ACTION == "RESTART"):
    SVC_ACTION = "Restart"
else:
    sys.exit("Invalid Action.  Choices are Start, Stop, or Restart (default)")
    
# Edit .env file to specify environment variables
from dotenv import load_dotenv
load_dotenv()

# Set DEBUG=True in .env to enable output of request/response headers and XML
DEBUG = os.getenv( 'DEBUG' ) == 'True'

# The WSDL is a local file in the working directory, see README
WSDL_FILE = './schema/ControlCenterServices.wsdl'

# This class lets you view the incoming and outgoing HTTP headers and XML
class MyLoggingPlugin( Plugin ):

    def egress( self, envelope, http_headers, operation, binding_options ):

        if not DEBUG: return

        # Format the request body as pretty printed XML
        xml = etree.tostring( envelope, pretty_print = True, encoding = 'unicode')

        print( f'\nRequest\n-------\nHeaders:\n{http_headers}\n\nBody:\n{xml}' )

    def ingress( self, envelope, http_headers, operation ):

        if not DEBUG: return

        # Format the response body as pretty printed XML
        xml = etree.tostring( envelope, pretty_print = True, encoding = 'unicode')

        print( f'\nResponse\n-------\nHeaders:\n{http_headers}\n\nBody:\n{xml}' )

# Create a SOAP client session

session = Session()

# We disable certificate verification by default
session.verify = False
# Suppress the console warning about the resulting insecure requests
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# To enabled SSL cert checking (recommended for production)
# place the CUCM Tomcat cert .pem file in the root of the project
# and uncomment the two lines below

# CERT = 'changeme.pem'
# session.verify = CERT

#Uncomment if setting session auth parameters in the environment
#session.auth = HTTPBasicAuth( os.getenv( 'AXL_USERNAME' ), os.getenv( 'AXL_PASSWORD' ) )
#Comment out if using environment parameters
session.auth = HTTPBasicAuth( AXL_USERNAME , AXL_PASSWORD)

transport = Transport( session = session, timeout = 10 )

# strict=False is not always necessary, but it allows zeep to parse imperfect XML
settings = Settings( strict = False, xml_huge_tree = True )

# If debug output is requested, add the MyLoggingPlugin class
plugin = [ MyLoggingPlugin() ] if DEBUG else [ ]

# Create the Zeep client with the specified settings
client = Client( WSDL_FILE, settings = settings, transport = transport, plugins = plugin )

start_time=time.time()

print('\nBeginning '+SVC_ACTION+' '+time.strftime("%H:%M:%S"))
# Open file containing list of UCM server addresses

filespec = './ucmlist.txt'
with open(filespec, 'r') as ucmlist:
    # Execute requested action for each UCM server listed in the file
    for CUCM_ADDRESS in ucmlist:
        CUCM_ADDRESS = CUCM_ADDRESS.strip()
        if len(CUCM_ADDRESS) == 0:
            print('\nWarning: Empty line in '+filespec+'\n')
            break
        print('\n'+bcolors.RESET+bcolors.OKGREEN+SVC_ACTION+' '+SVC_NAME+' at '+time.strftime("%H:%M:%S")+' for server '+bcolors.BOLDON+CUCM_ADDRESS)
        
        # Create the Zeep service binding to the Perfmon SOAP service at the specified CUCM
        service = client.create_service(
            '{http://schemas.cisco.com/ast/soap}ControlCenterServicesBinding',
            f'https://{ CUCM_ADDRESS }:8443/controlcenterservice2/services/ControlCenterServices' 
            )

        ServiceList = [SVC_NAME]
        ControlServicesDict = {'ControlType': SVC_ACTION,
        'ServiceList': {
                'item': ServiceList
            }
        }

        # Execute the request
        try:
            resp = service.soapDoControlServices( ControlServicesDict )
        except Fault as err:
            print( f'Zeep error: soapDoControlServices: { err }' )
            sys.exit( 1 )

        #print( "\nsoapDoControlServices response:\n" )

        # Create a simple report of the XML response
        print( 'Service Status' )
        print( ( '=' * 57 ) + '\n' )

        # Loop through the top-level of the response object
        for item in resp.ServiceInfoList.item:

            # Print the name and version, padding/truncating the name to 49 characters
            print( '{:50.50}'.format( item.ServiceName ) + item.ServiceStatus )

        #Check services status until they all are "Started"
        while True:
            try:
                resp = service.soapGetServiceStatus( ServiceList )
            except Fault as err:
                print( f'Zeep error: soapGetServiceStatus: { err }' )
                sys.exit( 1 )

            for item in resp.ServiceInfoList.item:
                print( '{:50.50}'.format( item.ServiceName ) + item.ServiceStatus )
                if item.ServiceStatus == 'Started':
                    ServiceList.remove(item.ServiceName)
            if len(ServiceList) > 0:
                time.sleep(5)
            else:
                break
elapsed_time = time.time()-start_time
print(bcolors.RESET+bcolors.BOLDON+'\nFinished '+SVC_ACTION+'. Elapsed time H:M:S: '+time.strftime("%H:%M:%S", time.gmtime(elapsed_time))+'\n')
