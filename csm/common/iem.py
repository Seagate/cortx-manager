#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          iem.py
 Description:       Interesting Event Messages (IEM) generation module

 Creation Date:     05/21/2020
 Author:            Oleg Babin

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import syslog


class Iem:
    SEVERITY_INFO = 'I'
    SEVERITY_WARN = 'W'
    SEVERITY_ERROR = 'E'
    SEVERITY_CRITICAL = 'C'

    IEC_CSM_SECURITY_SSL_CERT_EXPIRING = "0060010001" # IEC(CSM, SECURITY, SSL_CERT_EXPIRING)

    @staticmethod
    def generate(severity, iec, desc):
        iem = f"IEC:{severity}S{iec}:{desc}"
        syslog.syslog(iem)
