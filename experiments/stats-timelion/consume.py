import requests

class StatsConsumer:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def __post_to_timelion(self, data):
        """Posts TimeLion Api to fetch response"""
        timelion_api_endpoint = "http://%s:%s/api/timelion/run" % (
            self.host, self.port)
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json, text/plain, */*',
                   'kbn-xsrf': 'anything', 'Connection': 'keep-alive', }
        response = requests.post(url=timelion_api_endpoint, headers=headers,
                                 data=data)
        return response

    def receive(self, data):
        """Run's query for fetching data from timelion"""
        res = self.__post_to_timelion(data)
        res_json = res.json()
        return res_json
