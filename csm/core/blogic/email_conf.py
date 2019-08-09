#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          email_conf.py
 Description:       Contains functionality to config, enable, disable, show
                    email configuration.

 Creation Date:     27/11/2018
 Author:            Prasanna Kulkarni
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import os
import errno
from datetime import datetime
import sys
import shutil
import subprocess
from threading import Thread

from csm.common.cluster import Node, Cluster
from csm.common.file_collector import RemoteFileCollector
from csm.common.log import Log
from csm.common.conf import Conf
from csm.core.blogic import const
from csm.common.errors import CsmError

class EmailConfig(object):
    """ Logic to manage email configuration for syslog events.  """

    CA_CERTIFICATE    = "/etc/pki/tls/certs/ca-bundle.crt"
    SSMTP_TEMPL       = "/etc/ssmtp/ssmtp.conf.tmpl"
    SSMTP_CONF        = "/etc/ssmtp/ssmtp.conf"
    SSMTP_REVALIASES  = "/etc/ssmtp/revaliases"
    EMAIL_LIST_FILE   = "/etc/csm/email/email_list"

    def __init__(self):
        self._email_conf_dict = {
                                    "TLS_CA_FILE": EmailConfig.CA_CERTIFICATE,
                                    "mailhub": "",
                                    "FromLineOverride":"YES",
                                    "AuthUser": "",
                                    "AuthPass": "",
                                    "UseSTARTTLS": "Yes"
                                }
        self._ssmtp_conf_tmpl = EmailConfig.SSMTP_TEMPL
        self._ssmtp_conf = EmailConfig.SSMTP_CONF

    def configure(self, args, password = ""):
        """
        dumps dictionary to /etc/ssmtp/ssmtp.conf.
        """
        mail_hub = args[0]+":"+args[1]
        self._email_conf_dict["mailhub"] = mail_hub
        self._email_conf_dict["AuthUser"] = args[2]
        self._email_conf_dict["AuthPass"] = password
        try:
            File = open(EmailConfig.SSMTP_CONF, "w")
            for key in self._email_conf_dict.keys():
                conf_line = key+"="+self._email_conf_dict[key]+"\n"
                File.write(conf_line)
            File.close()
            File = open(EmailConfig.SSMTP_REVALIASES,"w")
            data = "root:"+args[2]+":"+mail_hub
            File.write(data)
            File.close()
            msg = 'Email configuration complete for email %s' %args[2]
            Log.info(msg)

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' %e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)
        return msg

    def unconfigure(self):
        """
        dumps dictionary to /etc/ssmtp/ssmtp.conf.
        """
        self._email_conf_dict["mailhub"] = ""
        self._email_conf_dict["AuthUser"] = ""
        self._email_conf_dict["AuthPass"] = ""
        try:
            File = open(EmailConfig.SSMTP_CONF, "w")
            for key in self._email_conf_dict.keys():
                conf_line = key+"="+self._email_conf_dict[key]+"\n"
                File.write(conf_line)
            File.close()
            msg = 'Email configuration is reset to default'
            Log.info(msg)

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' %e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)
        return msg

    def subscribe(self, args):
        """
        dumps dictionary to /etc/csm/email/email_list.
        """
        try:
            File = open(EmailConfig.EMAIL_LIST_FILE, "a")
            for email in args:
                File.write(email+"\n")
            File.close()
            msg = 'Subscription complete for emails '+(" ".join(args))
            Log.info(msg)

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' %e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)
        return msg

    def unsubscribe(self, args):
        """
        dumps dictionary to /etc/csm/email/email_list.
        """
        try:
            File = open(EmailConfig.EMAIL_LIST_FILE, "r")
            email_list = File.readlines()
            File.close()
            File = open(EmailConfig.EMAIL_LIST_FILE, "w")
            for email in args:
                line = email+"\n"
                if line in email_list: email_list.remove(line)
            File.write("".join(email_list))
            File.close()
            msg = 'Email '+(" ".join(args))+' unsubcribed.'
            Log.info(msg)

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' %e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)
        return msg

    def show(self):
        """
        shows current configuration file i.e. /etc/ssmtp/ssmtp.conf.
        """

        try:
            msg = "Email is not configured."
            if os.path.isfile(EmailConfig.SSMTP_CONF):
                File = open(EmailConfig.SSMTP_CONF, "r")
                conf = File.readline()
                while (conf != None and conf != ""):
                    if (conf.startswith("AuthUser")):
                        conf.strip("\n")
                        msg = "Sender: "+conf.split("=")[1]
                    conf = File.readline()
                File.close()
            if os.path.isfile(EmailConfig.EMAIL_LIST_FILE):
                File = open(EmailConfig.EMAIL_LIST_FILE, "r")
                conf = File.readlines()
                msg += "Subscribers: "+(", ".join(conf).replace("\n",""))
                File.close()
        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' %e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)
        return msg

    def _onerror(self, error):
        raise error
