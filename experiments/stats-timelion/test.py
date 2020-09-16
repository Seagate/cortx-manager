# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import datetime
import json
import os.path
import sys
import time

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
            "from": str(datetime.datetime.utcnow() - datetime.timedelta(minutes=1))[:19],
            "interval": "5s",
            "mode": "quick",
            "timezone": "UTC",
            "to": str(datetime.datetime.utcnow() + datetime.timedelta(minutes=1))[:19]
        }

    def send_stats(self):
        """Upload Stats to statsd"""
        if os.path.exists(self.stats_file):
            with open(self.stats_file) as json_file:
                data = json.load(json_file)
                for values in data['stats']:
                    self.prodObj.send(values['field'], values['value'], values['type'])
                self.test_case_params = data.get("test_case_params", [])

    @staticmethod
    def prepare_result(res_json):
        """This Function will prepare the aggregate sum of all the results."""
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
        """This Function will execute the test cases parsed into it."""
        status = "Passed"
        res_json = self.conObj.receive(json.dumps(query))
        actual_result = self.prepare_result(res_json)
        if expected_result != actual_result:
            status = "Failed"
        print(f"Test case  {test_case_number} {status}!!!!. Expected : {expected_result}"
              f", Actual : {actual_result}")

    def execute(self):
        """This Function Will Execute the Test Cases Added in sample file."""
        for each_test in self.test_case_params:
            query = {"sheet": [each_test.get("query")], "time": self.time}
            self.execute_each_test_case(query,
                                        each_test.get("test_case_number", 0),
                                        each_test.get("expected_result"))


if __name__ == "__main__":
    FILE_NAME, KIBANA_HOST, KIBANA_PORT, TIMELION_HOST, TIMELION_PORT = \
        sys.argv  # pylint: disable=unbalanced-tuple-unpacking
    stats_test_obj = StatsTest(KIBANA_HOST, KIBANA_PORT, "sample.json",
                               TIMELION_HOST, TIMELION_PORT)
    print("Sending stats to statsd...")
    stats_test_obj.send_stats()
    # Inserting Time Delay to let the data populate in timelion from statsd
    time.sleep(30)
    print("Running Test Cases... ")
    stats_test_obj.execute()
