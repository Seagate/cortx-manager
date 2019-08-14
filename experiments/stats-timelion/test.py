import os.path
import json
import datetime
import time
import sys
from consume import StatsConsumer
from export import StatsProducer

class StatsTest:
    def __init__(self, host, port, stats_file, timelion_host, timelion_port):
        self.host = host
        self.port = int(port)
        self.stats_file = stats_file
        self.prodObj = StatsProducer(host, int(port))
        self.conObj = StatsConsumer(timelion_host, int(timelion_port))
        self.test_case_params = []
        self.time = {
            "from": str(datetime.datetime.utcnow()-datetime.timedelta(minutes=1)
                        )[:19],
            "interval": "5s",
            "mode": "quick",
            "timezone": "UTC",
            "to": str(datetime.datetime.utcnow()+datetime.timedelta(minutes=1)
                      )[:19]
        }

    def send_stats(self):
        """
        Upload Stats to statsd
        """

        if os.path.exists(self.stats_file):
            with open(self.stats_file) as json_file:
                data = json.load(json_file)
                for values in data['stats']:
                    self.prodObj.send(values['field'], values['value'],
                                      values['type'])
                self.test_case_params = data.get("test_case_params", [])

    def prepare_result(self, res_json):
        """
        This Function will prepare the aggregate sum of all the results.
        """

        print(res_json)
        data_res = res_json['sheet'][0]['list']
        # This is just in case if the stats are sent more than one within the
        # time frame
        count = 0
        result_sum = 0
        for values in data_res[0]['data']:
            if float(values[1] or 0) != 0:
                result_sum = result_sum + float(values[1] or 0)
                count = count + 1
        result = result_sum / count if count != 0 else result_sum
        return float(result)

    def execute_each_test_case(self, query, test_case_number, expected_result):
        """
        This Function will execute the test cases parsed into it.
        """
        status = "Passed"
        res_json = self.conObj.receive(json.dumps(query))
        actual_result = self.prepare_result(res_json)
        if expected_result != actual_result:
            status = "Failed"
        print(
            f"Test case  {test_case_number} {status}!!!!.\
             Expected : {expected_result}, Actual : {actual_result}")

    def execute(self):
        """
        This Function Will Execute the Test Cases Added in sample file.
        """
        for each_test in self.test_case_params:
            query = {"sheet": [each_test.get("query")], "time": self.time}
            self.execute_each_test_case(query,
                                        each_test.get("test_case_number", 0),
                                        each_test.get("expected_result"))

if __name__ == "__main__":
    FILE_NAME, KIBANA_HOST, KIBANA_PORT, TIMELION_HOST, TIMELION_PORT = sys.argv
    statsTestObj = StatsTest(KIBANA_HOST, KIBANA_PORT, "sample.json",
                             TIMELION_HOST, TIMELION_PORT)
    print("Sending stats to statsd...")
    statsTestObj.send_stats()
    # Inserting Time Delay to let the data populate in timelion from statsd
    time.sleep(30)
    print("Running Test Cases... ")
    statsTestObj.execute()
