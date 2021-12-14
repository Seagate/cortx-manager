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

"""
    This is Stats service implementation
"""


# Let it all reside in a separate controller until we've all agreed on request
# processing architecture
from typing import Dict
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.log import Log
from csm.common.services import Service, ApplicationService
from csm.common.errors import CsmInternalError, InvalidRequest
from aiohttp import web
from csm.common.comm import MessageBusComm
from csm.plugins.cortx.convertor import Convertor
from csm.core.blogic import const

STATS_DATA_MSG_NOT_FOUND = "stats_not_found"

class StatsAppService(ApplicationService):
    """
    Provides operations on stats without involving the domain specifics
    """
    BUFFER = []
    def __init__(self, stats_provider, metrics_client):
        self._stats_provider = stats_provider
        self.metrics_client = metrics_client
        self.metrics_client.init(type=const.PRODUCER,
                            producer_id=Conf.get(const.CSM_GLOBAL_INDEX,
                                                const.MSG_BUS_PERF_STAT_PRODUCER_ID),
                            message_type=Conf.get(const.CSM_GLOBAL_INDEX,
                                                const.MSG_BUS_PERF_STAT_MSG_TYPE),
                            method=Conf.get(const.CSM_GLOBAL_INDEX,
                                                const.MSG_BUS_PERF_STAT_METHOD))
        if self.metrics_client:
                self.metrics_client.init(type='consumer', consumer_id='csm',
                    consumer_group='csm_group', consumer_message_types=["perf_stat"],
                    auto_ack=False, offset="latest")
        self.convertor_type = const.STATS_CONVERTOR
        self.convertor = Convertor(self.convertor_type)

    async def get(self, stats_id, panel, from_t, to_t,
                  metric_list, interval, total_sample, unit, output_format, query) -> Dict:
        """
        Fetch specific statistics for panel - full parameter set
        :return: :type:list
        """
        Log.debug(f"Get panel: {panel} stats")
        output = {}
        if stats_id:
            output["id"]=stats_id
        panel_data =  await self._stats_provider.process_request(stats_id = stats_id, panel = panel,
                                                  from_t = from_t, duration_t = to_t,
                                                  metric_list = metric_list,
                                                  interval = interval,
                                                  total_sample = total_sample,
                                                  unit = unit.lower(),
                                                  output_format = output_format,
                                                  query = query)
        output["metrics"] = panel_data["list"]
        Log.debug(f"Stats Request Output: {output}")
        return output

    async def get_labels(self, panel):
        """
        Fetch available labels for panel
        """
        label_list_dict_keys = await self._stats_provider.get_labels(panel)
        return {"label_list": list(label_list_dict_keys)}

    async def get_axis(self, panel):
        """
        Fetch axis unit for selected panel
        """
        return {"axis_unit": await self._stats_provider.get_axis(panel)}

    async def get_panel_list(self):
        """
        Fetch Panels and metrics list for use with special metrics requests
        """
        panel_list_dict_keys = await self._stats_provider.get_panels()
        metric_list_dict_keys = await self._stats_provider.get_metrics()
        units_list_dict_keys = await self._stats_provider.get_all_units()
        return {"panel_list": list(panel_list_dict_keys),
                "metric_list": list(metric_list_dict_keys),
                "unit_list": list(units_list_dict_keys)}

    async def get_panels(self, stats_id, panels_list, from_t, to_t, interval,
                         total_sample, output_format) -> Dict:
        """
        Fetch statistics for selected panels list (simplified - reduced parameter set)
        """
        Log.debug(f"Get stats for panels: {panels_list}")
        output = {}
        if stats_id:
            output["id"]=stats_id
        data_list = []
        for panel in panels_list:
            panel_data = await self._stats_provider.process_request(
                                                  stats_id = stats_id,
                                                  panel = panel,
                                                  from_t = from_t, duration_t = to_t,
                                                  metric_list = "",
                                                  interval = interval,
                                                  total_sample = total_sample,
                                                  unit = "",
                                                  output_format = output_format,
                                                  query = "")
            data_list.extend(panel_data["list"])
        output["metrics"] = data_list
        Log.debug(f"Stats Request Output: {output}")
        return output

    async def get_metrics(self, stats_id, metrics_list, from_t, to_t, interval,
                          total_sample, output_format) -> Dict:
        """
        Fetch statistics for selected panel.metric list (simplified - reduced parameter set)
        panels : { "<panel>": {"metric":[...], "unit":[...]}}
        """
        Log.debug("Get metrics requested: id=%s, interval=%s" %(str(stats_id), interval))
        output = {}
        panels = {}
        try:
            for metric in metrics_list:
                li = metric.split(".")
                if li[0] not in panels:
                    panels[li[0]] = {"metric": [li[1]], "unit":[]}
                else:
                    panels[li[0]]["metric"].append(li[1])
                if len(li) == 2:
                    panels[li[0]]["unit"].append("")
                else:
                    panels[li[0]]["unit"].append(li[2])
        except (IndexError, KeyError):
            raise InvalidRequest("Invalid metric list for Stats %s" %metrics_list)

        if stats_id:
            output["id"]=stats_id
        data_list = []
        for panel in panels.keys():
            panel_data = await self._stats_provider.process_request(
                                                  stats_id = stats_id,
                                                  panel = panel,
                                                  from_t = from_t, duration_t = to_t,
                                                  metric_list = panels[panel]["metric"],
                                                  interval = interval,
                                                  total_sample = total_sample,
                                                  unit = panels[panel]["unit"],
                                                  output_format = output_format,
                                                  query = "")
            data_list.extend(panel_data["list"])
        output["metrics"] = data_list
        Log.debug(f"Stats Request Output: {output}")
        return output

    def _convertor(self, message):
        converted_message = self.convertor.convert_data(message)
        return converted_message

    def _stats_callback(self, message):
        # TODO: aggregation()
        converted_message = self._convertor(message)
        StatsAppService.BUFFER.append(converted_message)

    async def get_perf_metrics(self):
        """Fetch metrics from message bus and expose it in required format"""
        StatsAppService.BUFFER = []
        self.metrics_client.recv(self._stats_callback, is_blocking=False)
        return StatsAppService.BUFFER
    
    def stop_msg_bus(self):
        Log.info("Stopping Messagebus")
        self.metrics_client.stop()

    async def post_perf_metrics_to_msg_bus(self, messages):
        try:
            Log.info(f"Publish {len(messages)} messages:{messages} to message bus")
            self.metrics_client.send(messages)
            return {"response":f"{len(messages)} messages published successfully."}
        except Exception as e:
            Log.error(f"Error occured while sending message to message bus:{e}")
            raise CsmInternalError(f"Error occured while sending message to message bus:{e}")
