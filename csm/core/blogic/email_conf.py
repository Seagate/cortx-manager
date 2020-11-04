#!/usr/bin/env python3
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


class EmailConfig:
    """Logic to manage email configuration for syslog events."""
    CA_CERTIFICATE = "/etc/pki/tls/certs/ca-bundle.crt"
    SSMTP_TEMPL = "/etc/ssmtp/ssmtp.conf.tmpl"
    SSMTP_CONF = "/etc/ssmtp/ssmtp.conf"
    SSMTP_REVALIASES = "/etc/ssmtp/revaliases"
    EMAIL_LIST_FILE = "/etc/csm/email/email_list"

    def __init__(self):
        self._email_conf_dict = {
            "TLS_CA_FILE": EmailConfig.CA_CERTIFICATE,
            "mailhub": "",
            "FromLineOverride": "YES",
            "AuthUser": "",
            "AuthPass": "",
            "UseSTARTTLS": "Yes"
        }
        self._ssmtp_conf_tmpl = EmailConfig.SSMTP_TEMPL
        self._ssmtp_conf = EmailConfig.SSMTP_CONF

    def configure(self, args, password=""):
        """dumps dictionary to /etc/ssmtp/ssmtp.conf."""
        mail_hub = f"{args[0]}:{args[1]}"
        self._email_conf_dict["mailhub"] = mail_hub
        self._email_conf_dict["AuthUser"] = args[2]
        self._email_conf_dict["AuthPass"] = password
        try:
            file_var = open(EmailConfig.SSMTP_CONF, "w")
            for key in self._email_conf_dict:
                conf_line = f"{key}={self._email_conf_dict[key]}\n"
                file_var.write(conf_line)
            file_var.close()
            file_var = open(EmailConfig.SSMTP_REVALIASES, "w")
            data = f"root:{args[2]}:{mail_hub}"
            file_var.write(data)
            file_var.close()
            msg = 'Email configuration complete for email %s' % args[2]
            Log.info(msg)

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, str(e))

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, str(e))
        return msg

    def unconfigure(self):
        """dumps dictionary to /etc/ssmtp/ssmtp.conf."""
        self._email_conf_dict["mailhub"] = ""
        self._email_conf_dict["AuthUser"] = ""
        self._email_conf_dict["AuthPass"] = ""
        try:
            file_var = open(EmailConfig.SSMTP_CONF, "w")
            for key in self._email_conf_dict:
                conf_line = f"{key}={self._email_conf_dict[key]}\n"
                file_var.write(conf_line)
            file_var.close()
            msg = 'Email configuration is reset to default'
            Log.info(msg)

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, str(e))

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, str(e))
        return msg

    @staticmethod
    def subscribe(args):
        """dumps dictionary to /etc/csm/email/email_list."""
        try:
            file_var = open(EmailConfig.EMAIL_LIST_FILE, "a")
            for email in args:
                file_var.write(f"{email}\n")
            file_var.close()
            msg = f'Subscription complete for emails {" ".join(args)}'
            Log.info(msg)

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, str(e))

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, str(e))
        return msg

    @staticmethod
    def unsubscribe(args):
        """dumps dictionary to /etc/csm/email/email_list."""
        try:
            file_var = open(EmailConfig.EMAIL_LIST_FILE, "r")
            email_list = file_var.readlines()
            file_var.close()
            file_var = open(EmailConfig.EMAIL_LIST_FILE, "w")
            for email in args:
                line = f"{email}\n"
                if line in email_list:
                    email_list.remove(line)
            file_var.write("".join(email_list))
            file_var.close()
            msg = f'Email {" ".join(args)} unsubscribed.'
            Log.info(msg)

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, str(e))

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, str(e))
        return msg

    @staticmethod
    def show():
        """shows current configuration file i.e. /etc/ssmtp/ssmtp.conf."""
        try:
            msg = "Email is not configured."
            if os.path.isfile(EmailConfig.SSMTP_CONF):
                file_var = open(EmailConfig.SSMTP_CONF, "r")
                conf = file_var.readline()
                while (conf is not None and conf != ""):
                    if conf.startswith("AuthUser"):
                        conf.strip("\n")
                        msg = f'Sender: {conf.split("=")[1]}'
                    conf = file_var.readline()
                file_var.close()
            if os.path.isfile(EmailConfig.EMAIL_LIST_FILE):
                file_var = open(EmailConfig.EMAIL_LIST_FILE, "r")
                conf = file_var.readlines()
                msg += "Subscribers: " + ", ".join(conf).replace("\n", "")
                file_var.close()
        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, str(e))

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, str(e))
        return msg

    @staticmethod
    def _onerror(error):
        raise error
