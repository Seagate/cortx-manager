import sys
from csm.eos.plugins.alert import Alerts
import json
import threading

class Alert(object):
    def __init__(self):
        # TODO
        pass

    def get(self, **kwargs):
        # TODO
        pass

    def acknowledge(self, id):
        # TODO
        pass

    def configure(self):
        # TODO
        pass

class AlertMonitor(object):
    def __init__(self):
        '''
        Initializes the Alert Plugin
        '''
        self.obj = Alerts()
        self.data = {}

    def _start_plugin(self):
        '''
        This method acts as a thread function. It will start the alert plugin in a seprate thread.
        This method passes consume_alert as a callback function to alert plugin.
        '''
        self.obj.init(callback_fn=self.consume_alert)

    def monitor(self):
        '''
        This method creats and starts an alert monitor thread
        '''
        amqp_thread = threading.Thread(target=self._start_plugin, args=())
        amqp_thread.start()

    def consume_alert(self, message):
        '''
        This is a callback function on which alert plugin will send the alerts in JSON format.
        1. Upon receiving the alert it is converted to output schema.
        2. The output schema is then stored to DB.
        3. The same schema is published over web sockets.
        4. After perfoming the above 3 tasks a boolean value (Ture is success and False if some error) is returned.
           This return value will be used by alert plugin to decide whether to acknowledge the alert or not.
        '''
        # TODO : The above mentioned 3 tasks
        output_schema = self.create_output_schema(json.loads(message))
        return False

    def create_output_schema(self, message):
        ''' Parsing the alert JSON to create the output schema'''
        data['stats'] = []
        dict = message['message']['sensor_response_type']
        for values in dict.values():
            data['stats'].append({'time': '%s' %(message['time']), 'alert_type': '%s' %(values['alert_type']), 'status': '%s' %(values['info']['status']), 'location': '%s' %(values[    'info']['location']), 'health-reason': '%s' %(values['info']['health-reason']), 'comment': '', 'acknowledge': '', 'resolved': ''})
        return data
