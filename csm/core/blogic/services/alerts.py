#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          api_client.py
 Description:       Infrastructure for invoking business logic locally or
                    remotely or various available channels like REST.

 Creation Date:     31/05/2018
 Author:            Malhar Vora
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
# Let it all reside in a separate controller until we've all agreed on request
# processing architecture
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict

from csm.common.errors import CsmNotFoundError, CsmError
from csm.core.blogic.alerts.alerts import AlertsService, ALERTS_ERROR_NOT_FOUND

ALERT_ERROR_INVALID_DURATION = "alert_invalid_duration"


class AlertsAppService:
    """
        Provides operations on alerts without involving the domain specifics
    """

    # TODO: In the case of alerts, we probably do not need another alert-related
    # service

    def __init__(self, service: AlertsService):
        self.service = service

    async def _call_nonasync(self, function, *args):
        """
            This function allows to await on synchronous code.
            It won't be needed once we switch to asynchronous code everywhere.

            :param function: A callable
            :param args: Positional arguments that will be passed to the function
            :returns: the result returned by 'function'
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, function, *args)

    async def update_alert(self, alert_id, data):
        """
        Update the Data of Specific Alerts
        :param alert_id: id for the alert
        :param data: data to be updated for the alert
        :return:
        """
        result = await self._call_nonasync(self.service.update_alert, alert_id,
                                           data)
        return result.data()

    async def fetch_all_alerts(self, duration, direction, sort_by, offset,
                               page_limit) -> Dict:
        """
        Fetch All Alerts
        :param duration: time duration for range of alerts
        :param direction: direction of sorting asc/desc
        :param sort_by: key by which sorting needs to be performed.
        :param offset: offset page
        :param page_limit: no of records to be displayed on page.
        :return: :type:list
        """
        # TODO: The storage must provide a function to fetch alerts with respect to
        # parameters and orderings requried by the business logic.
        alerts_obj = await self._call_nonasync(self.service.fetch_all_alerts)
        if alerts_obj:
            reverse = True if direction == 'desc' else False
            alerts_obj = sorted(alerts_obj, key=lambda item: item.data()[sort_by],
                                reverse=reverse)
            if duration:  # Filter
                # TODO: time format can generally be API-dependent. Better pass here an already
                # parsed TimeDelta object.
                time_duration = int(re.split(r'[a-z]', duration)[0])
                time_format = re.split(r'[0-9]', duration)[-1]
                dur = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
                if time_format not in dur.keys():
                    raise CsmError(ALERT_ERROR_INVALID_DURATION,
                            "Invalid Parameter for Duration")
                end_time = datetime.now().timestamp()
                start_time = (datetime.utcnow() - timedelta(
                    **{dur[time_format]: time_duration})).timestamp()
                alerts_obj = list(
                    filter(lambda x: start_time < x['created_time'] < end_time,
                           alerts_obj))
            if offset and int(offset) >= 1:
                offset = int(offset)
                if page_limit  and int(page_limit) > 0:
                    page_limit = int(page_limit)
                    alerts_obj = [alerts_obj[i:i + page_limit] for i in
                                  range(0, len(alerts_obj), page_limit)]

                alerts_obj = alerts_obj[int(offset) - 1]

        return {"total_records": len(alerts_obj), "alerts": alerts_obj.data()}

    async def fetch_alert(self, alert_id):
        # This method is for debugging purposes only
        alert = await self._call_nonasync(self.service.fetch_alert, alert_id)
        if not alert:
            raise CsmNotFoundError(ALERTS_ERROR_NOT_FOUND, "Alert is not found")
        return alert.data()
