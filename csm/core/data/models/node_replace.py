#!/usr/bin/env python3
"""
 ****************************************************************************
 Filename:          node_replace.py
 Description:       Node Replace Db Model

 Creation Date:     26/06/2020
 Author:            Prathamesh Rodi

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from datetime import datetime, timezone
from schematics.types import StringType, DateTimeType, IntType
from csm.core.blogic.models import CsmModel


class ReplaceNode(CsmModel):
    _id = "job_id"

    node_id = StringType()
    job_id = StringType()
    status = StringType()
    hostname = StringType()
    ssh_port = IntType()
    created_time = DateTimeType()
    updated_time = DateTimeType()

    @staticmethod
    def generate_new(job_id, node_id, hostname, ssh_port):
        """

        :param job_id:
        :param node_id:
        :return:
        """
        replace_node_obj = ReplaceNode()
        replace_node_obj.job_id = job_id
        replace_node_obj.node_id = node_id
        replace_node_obj.hostname = hostname
        replace_node_obj.ssh_port = ssh_port
        replace_node_obj.status = JobStatus.Is_Running
        replace_node_obj.created_time = datetime.now(timezone.utc)
        replace_node_obj.updated_time = datetime.now(timezone.utc)
        return replace_node_obj


class JobStatus:
    """
    Repository Class for Node Replacement.
    """
    Is_Running = "Running"
    Completed = "Completed"
    Not_Running = "Not Running"

