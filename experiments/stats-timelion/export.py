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

from socket import AF_INET, SOCK_DGRAM, socket


class StatsProducer:
    SC_TIMING = "ms"
    SC_COUNT = "c"
    SC_GAUGE = "g"

    def __init__(self, host, port):
        self.addr = (host, port)

    def send_time_stats(self, stats, value):
        self.send_stats(stats, value, self.SC_TIMING)

    def send_gauge_stats(self, stats, value):
        self.send_stats(stats, value, self.SC_GAUGE)

    def send_count_stats(self, stats, value):
        self.send_stats(stats, value, self.SC_COUNT)

    def send_stats(self, stats, value, stats_type):
        stats = self.format(stats, value, stats_type)
        self.send_udp(stats, self.addr)

    def send(self, field, value, stats_type):
        if stats_type == self.SC_COUNT:
            self.send_count_stats(field, value)
        elif stats_type == self.SC_TIMING:
            self.send_time_stats(field, value)
        else:
            self.send_gauge_stats(field, value)

    @staticmethod
    def format(keys, value, stats_type):
        """Format the data into a stats sample so it can be sent to stats framework"""
        data = {}
        value = f"{value}|{stats_type}"
        if not isinstance(keys, (list, tuple)):
            keys = [keys]
        for key in keys:
            data[key] = value
        return data

    @staticmethod
    def send_udp(stats, addr):
        """Sends stats to a given stats server"""
        udp_sock = socket(AF_INET, SOCK_DGRAM)
        for item in stats.items():
            print(item)
            udp_sock.sendto(":".join(item).encode('utf-8'), addr)
