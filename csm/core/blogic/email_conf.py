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

import os
from cortx.utils.log import Log
from csm.common.errors import CsmError

class EmailConfig(object):
    """Logic to manage email configuration for syslog events."""

    CA_CERTIFICATE    = "/etc/pki/tls/certs/ca-bundle.crt"
    SSMTP_TEMPL       = "/etc/ssmtp/ssmtp.conf.tmpl"
    SSMTP_CONF        = "/etc/ssmtp/ssmtp.conf"
    SSMTP_REVALIASES  = "/etc/ssmtp/revaliases"
    EMAIL_LIST_FILE   = "/etc/csm/email/email_list"

    def __init__(self):
        """Email config init."""
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
        """Dumps dictionary to /etc/ssmtp/ssmtp.conf."""
        mail_hub = args[0]+":"+args[1]
        self._email_conf_dict["mailhub"] = mail_hub
        self._email_conf_dict["AuthUser"] = args[2]
        self._email_conf_dict["AuthPass"] = password
        try:
            File = open(EmailConfig.SSMTP_CONF, "w")
            for key in self._email_conf_dict:
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
            for key in self._email_conf_dict:
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
        """Dumps dictionary to /etc/csm/email/email_list."""
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
        """Dumps dictionary to /etc/csm/email/email_list."""
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
        """Shows current configuration file i.e. /etc/ssmtp/ssmtp.conf."""
        try:
            msg = "Email is not configured."
            if os.path.isfile(EmailConfig.SSMTP_CONF):
                File = open(EmailConfig.SSMTP_CONF, "r")
                conf = File.readline()
                while (conf is not None and conf != ""):
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
