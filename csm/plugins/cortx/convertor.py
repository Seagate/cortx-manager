from abc import ABCMeta, abstractmethod
from cortx.utils.log import Log
from csm.common.errors import CsmInternalError, InvalidRequest
import re

class Prometheus:
    """
    Convert metrics/stats into promethues format
    """

    def __init__(self):
        pass

    def convert(self, message):
        Log.debug(f"Converting to prometheus format: {message}")
        message = "health_check_request_count:1|c"
        splitted_mssg = re.split("\|", message)
        messg, mssg_type = splitted_mssg[0], splitted_mssg[1]
        if mssg_type == "c" or  mssg_type == "g":
            message =  re.sub(":", " ", messg)
        elif mssg_type == "ms":
            pass
            #TODO: timer is not supported in prometheus
        else:
            raise InvalidRequest("Invalid type of stats/metric detected %s" %mssg_type)
        return message

class Statsd:
    """
    Convert metrics/stats into statsd format
    """
    
    def __init__(self):
        pass

    def convert(self, message):
        """Given message is currently already in statd format so no need to convert it further"""
        # TODO: we can add validation logic for statsd format.
        Log.debug(f"Converting to statsd format: {message}")
        return message

class CovertorFactory:
    """
    Provides interface to access diffrent convertors for metrics/stats into specific format
    """
    def __init__(self, tool="Prometheus"):
        self.tool = tool
        self.tools = {
            "Prometheus": Prometheus,
            "Statsd": Statsd
        }
    def get_instance(self):
        return self.tools[self.tool]()

class Convertor:
    def __init__(self, tool):
        self.obj = CovertorFactory(tool).get_instance()

    def convert_data(self, data):
        return self.obj.convert(data)