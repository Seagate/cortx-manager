"""
 ****************************************************************************
 Filename:          alerts.py
 Description:       Contains functionality for alert plugin.

 Creation Date:     12/08/2019
 Author:            Pawan Kumar Srivastava

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys
from csm.eos.plugins.alert import AlertPlugin
from csm.common.errors import CsmError
import json
import threading
import errno

class Alert(object):
    """ Represents an alert to be sent to front end """

    def __init__(self):
        # TODO
        pass

    def get(self, **kwargs):
        # TODO
        raise CsmError(errno.ENOSYS, 'Alert.get() not implemented') 

    def acknowledge(self, id):
        # TODO
        raise CsmError(errno.ENOSYS, 'Alert.acknowledge() not implemented') 

    def configure(self):
        # TODO
        raise CsmError(errno.ENOSYS, 'Alert.configure() not implemented') 

class AlertMonitor(object):
    """ 
    Alert Monitor works with AmqpComm to monitor alerts. 
    When Alert Monitor receives a subscription request, it scans the DB and 
    sends all pending alerts. It is assumed currently that there can be only 
    one subscriber at any given point of time. 
    Then it waits for AmqpComm to notice if there are any new alert. 
    Alert Monitor takes action on the received alerts using a callback. 
    Actions include (1) storing on the DB and (2) sending to subscribers, i.e. web server. 
    """

    def __init__(self):
        """
        Initializes the Alert Plugin
        """
        self.obj = AlertPlugin()
        self.data = {}

    def _monitor(self):
        """
        This method acts as a thread function. 
        It will start the alert plugin in a seprate thread.
        This method passes consume_alert as a callback function to alert plugin.
        """
        self.obj.init(callback_fn=self.consume_alert)

    def start(self):
        """
        This method creats and starts an alert monitor thread
        """
        amqp_thread = threading.Thread(target=self._monitor, args=())
        amqp_thread.start()

    def consume_alert(self, message):
        """
        This is a callback function on which alert plugin will send the alerts in JSON format.
        1. Upon receiving the alert it is converted to output schema.
        2. The output schema is then stored to DB.
        3. The same schema is published over web sockets.
        4. After perfoming the above 3 tasks a boolean value 
           (Ture is success and False if some error) is returned.
        5. This return value will be used by alert plugin to decide 
           whether to acknowledge the alert or not.
        """
        # TODO : The above mentioned 3 tasks
        output_schema = self.create_output_schema(json.loads(message))
        return False

    def create_output_schema(self, message):
        """ 
        Parsing the alert JSON to create the output schema
        """
        data = {'$schema': 'http://json-schema.org/draft-03/schema#', \
                 'id': 'http://json-schema.org/draft-03/schema#', \
                 'title': 'CSM HW Schema', 'type': 'object', \
                 'properties': {'header': {}, 'hw': {}}}
        dict = message['message']['sensor_response_type']
        for values in dict.values():
            data['properties']['header'] = {'type': 'hw', 'alert_type': '%s'\
                    %(values.get('alert_type', "")), 'type': 'hw', 'status': '%s'\
                    %(values.get('info', {}).get('status', '')), 'resolved': 'no'\
                    , 'acknowledged': 'no', 'description': '%s'\
                    %(values.get('info', {}).get('health-reason', '')),\
                     'location': '%s' %(values.get('info', {}).get('location', '')),\
                     'severity': '1', 'recommendation': '%s'\
                     %(values.get('info', {}).get('health-recommendation', ''))}
            data['properties']['hw'] = {'vendor': '%s' %(values.get('info', {})\
                    .get('vendor', '')), 'enclosure_id': '%s'\
                    %(values.get('info', {}).get('enclosure-id', '')), \
                    'serial_number': '%s' %(values.get('info', {})\
                    .get('serial-number', '')), 'part_number': '%s'\
                    %(values.get('info', {}).get('part-number', ''))}
        return data
