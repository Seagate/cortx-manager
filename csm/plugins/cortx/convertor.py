from abc import ABCMeta, abstractmethod
from cortx.utils.log import Log
from csm.common.errors import CsmInternalError, InvalidRequest
import re

class Iconvertor(metaclass=ABCMeta):
    """
    Provides interface to access diffrent convertors for metrics/stats into specific format
    """

    @abstractmethod
    def convertor():
        """Interface method to convert metrics into specific format"""
        pass

class Prometheus_convertor(Iconvertor):
    """
    Convert metrics/stats into promethues format
    """

    def  _covert_counter(self, messg):
        """ Convert to promethues counter type metrics"""
        converted_mssg = re.sub(":", " ", messg)
        return converted_mssg

    def convertor(self, message):
        Log.debug(f"Converting to prometheus format: {message}")
        splitted_mssg = re.split("\|", message)
        messg, type = splitted_mssg[0], splitted_mssg[1]
        if type == "c":
            message = self._covert_counter(messg)
        elif type == "g":
            pass
            #TODO: add other types timer, set etc
        else:
            raise InvalidRequest("Invalid type of stats/metric detected %s" %type)
        return message

class Statsd_convertor(Iconvertor):
    """
    Convert metrics/stats into statsd format
    """

    def convertor(self, message):
        """Given message is currently already in statd format so no need to convert it further"""
        # TODO: we can add validation logic for statsd format.
        Log.debug(f"Converting to statsd format: {message}")
        return message


class Convertor:
    """
    Provides a way to convert metrics/stats into specific format
    """
    @staticmethod
    def init_convertor(convertor_type):
        if convertor_type == "prometheus" or convertor_type == "Prometheus"  :
            return  Prometheus_convertor()
        elif convertor_type == "statsd":
            return  Statsd_convertor()
        else:
            raise InvalidRequest("Invalid type of convertor requested %s" %convertor_type)
