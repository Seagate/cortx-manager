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
import subprocess
import errno

from csm.common.comm import SSHChannel
from cortx.utils.log import Log
from csm.core.blogic import const
from csm.common.errors import CsmError


class FileCollector(object):
    """ Base class of File collector. """
    def __init__(self, collection_rules, target_path):
        """
        Collection rules relate component to its bundle spec. It contains
        list of components each containing rules i.e.
        1. List of commands that need to run on the node and obtain output
        2. List of files to be downloaded from the node
        3. target where the command output and files will be consolidated
        4. Commands to run for cleanup, if any

        Collection rules defined as map with component as key with rules
            [<component>] =
                'commands' : [List of commands]
                'files'    : [List of files]
            [<component>] = ...
        """

        if collection_rules is None:
            raise CsmError(errno.EINVAL, 'invalid component spec. Check configuration')

        self._collection_rules = collection_rules
        self._target = target_path

    def collect(self, comp_name_list):
        """
        Collect the predefined information from given node. This is
        done in steps.
        1. Init operations e.g. create directory
        2. execute commands (as per component rules)
        3. Collect files
        4. Clean up

        These steps are implemented in derived class
        """

        try:
            self._startup()
            for comp_name in comp_name_list:
                if comp_name not in self._collection_rules.keys():
                    Log.error('Invalid component %s. Valid: %s'
                              % (comp_name, self._collection_rules.keys()))
                    raise CsmError(errno.EINVAL, 'Invalid component %s' % comp_name)
                    # TODO - Raise proper Exception

                out_dir = os.path.join(self._target, comp_name)
                os.makedirs(out_dir)

                Log.debug('collecting %s data into %s' % (comp_name, out_dir))
                self._execute_commands(comp_name, out_dir)

                # File specs may contain wild-card characters e.g. 'debug.*'
                # Expand them first
                file_list = []
                for file_spec in self._collection_rules[comp_name]['files']:
                    Log.debug('file_spec: %s' % file_spec)
                    file_list.extend(self._expand_file_spec(file_spec))

                self._collect_files(file_list, out_dir)

            self._cleanup()

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' % e)

        except IOError as e:
            Log.exception(e)
            raise CsmError(errno.EIO, '%s' % e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' % e)


class LocalFileCollector(FileCollector):
    """ Collects files from the local machine """

    def __init__(self, collection_rules, target_path):
        super(LocalFileCollector, self).__init__(collection_rules, target_path)

    def _startup(self):
        """ Create bundling tmp directory for local node. """

    def _execute_commands(self, comp_name, out_dir):
        """ Execute the commands """

        with open(os.path.join(out_dir, const.SUMMARY_FILE), 'w') as summary:
            for cmd in self._collection_rules[comp_name]['commands']:
                try:
                    Log.debug('$ %s' % cmd)
                    summary.write('$ %s\n' % cmd)
                    output = subprocess.check_output(cmd,
                                                     stderr=subprocess.PIPE, shell=True)
                    summary.write(output)

                except (OSError, subprocess.CalledProcessError) as exc:
                    Log.error('%s %s' % (exc.__class__.__name__, str(exc)))

    def _expand_file_spec(self, file_spec):
        Log.debug('file_spec: %s' % file_spec)
        cmd = 'ls %s' % file_spec
        output = subprocess.check_output(cmd, stderr=subprocess.PIPE, shell=True)
        return output.split('\n')

    def _collect_files(self, file_list, out_dir):
        """ Collect files from various logging sources """

        Log.debug('file_list: %s' % file_list)
        files = ' '.join(file_list)
        tar_cmd = 'tar czvf %s %s' % (os.path.join(out_dir, const.BUNDLE_FILE), files)
        try:
            Log.debug('$ %s' % tar_cmd)
            subprocess.check_output(tar_cmd, stderr=subprocess.PIPE, shell=True)

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' % e)

        except IOError as e:
            Log.exception(e)
            raise CsmError(errno.EIO, '%s' % e)

        except (subprocess.CalledProcessError) as e:
            Log.exception(e)
            raise CsmError(-1, '%s' % e)

    def _cleanup(self):
        pass


class RemoteFileCollector(FileCollector):
    """ Collects files from the Remote machine """

    def __init__(self, collection_rules, node, user, target_path):
        super(RemoteFileCollector, self).__init__(collection_rules, target_path)
        self._channel = SSHChannel(node, user, True)
        self._tmp_file = 'files.tgz'
        self._node = node
        self._user = user

    def _startup(self):
        """ Initialization before the data is collected """
        self._channel.connect()

    def _execute_commands(self, comp_name, out_dir):
        """ Execute the commands """

        with open(os.path.join(out_dir, const.SUMMARY_FILE), "w") as summary:
            if self._collection_rules[comp_name]['commands'] is None:
                return
            for action in self._collection_rules[comp_name]['commands']:
                try:
                    summary.write('\n$ %s\n' % action)
                    rc, output = self._channel.execute(action)
                    summary.write('%s\n' % output)

                except OSError as e:
                    Log.exception(e)
                    raise CsmError(e.errno, '%s' % e)

                except IOError as e:
                    Log.exception(e)
                    raise CsmError(errno.EIO, '%s' % e)

                except (subprocess.CalledProcessError) as e:
                    Log.exception(e)
                    raise CsmError(-1, '%s' % e)

    def _expand_file_spec(self, file_spec):
        cmd = 'ls %s' % file_spec
        rc, output = self._channel.execute(cmd)
        return output.split('\n')

    def _collect_files(self, file_list, out_dir):
        """ Collect files from remote nodes and copy it to bucket """

        local_file = os.path.join(out_dir, self._tmp_file)
        remote_file = os.path.join('/tmp', self._tmp_file)

        files = ' '.join(file_list)
        tar_cmd = 'tar czvf %s %s' % (remote_file, files)

        try:
            Log.debug('cmd: %s' % tar_cmd)
            output, error = self._channel.execute(tar_cmd)
            Log.debug('Copy remote:%s local:%s' % (remote_file, local_file))
            self._channel.recv_file(remote_file, local_file)
            self._channel.execute('rm -f %s' % remote_file)

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' % e)

        except IOError as e:
            Log.exception(e)
            raise CsmError(errno.EIO, '%s' % e)

        except (subprocess.CalledProcessError) as e:
            Log.exception(e)
            raise CsmError(-1, '%s' % e)

    def _cleanup(self):
        """ Clean all the temp files and the directory """
        self._channel.disconnect()
