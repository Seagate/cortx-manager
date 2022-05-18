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

import subprocess
import asyncio


class Process:
    def __init__(self, cmd):
        self._cmd = cmd

    def run(self, **kwargs):
        pass


class SimpleProcess(Process):
    """Execute process and provide output."""

    def __init__(self, cmd):
        super(SimpleProcess, self).__init__(cmd)
        self.shell = False
        self.cwd = None
        self.timeout = None
        self.env = None
        self.universal_newlines = None

    def run(self, **kwargs):
        """Run simple process."""
        for key, value in kwargs.items():
            setattr(self, key, value)

        try:
            cmd = self._cmd.split() if isinstance(self._cmd, str) else self._cmd
            self._cp = subprocess.run(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=self.shell, cwd=self.cwd,
                                      timeout=self.timeout, env=self.env,
                                      universal_newlines=self.universal_newlines)

            self._output = self._cp.stdout
            self._err = self._cp.stderr
            self._returncode = self._cp.returncode
            return self._output, self._err, self._returncode
        except Exception as err:
            self._err = "SubProcess Error: " + str(err)
            self._output = ""
            self._returncode = -1
            return self._output, self._err, self._returncode


class PipedProcess(Process):
    """Execute process with pipe and provide output."""

    def __init__(self, cmd):
        super(PipedProcess, self).__init__(cmd)

    def run(self, **kwargs):
        # TODO
        pass

class AsyncioSubprocess(Process):
    def __init__(self, cmd):
        super(AsyncioSubprocess, self).__init__(cmd)

    async def run(self, **kwagrs):
        try:
            self._process = await asyncio.create_subprocess_shell(self._cmd,
                                                                  stdout=asyncio.subprocess.PIPE,
                                                                  stderr=asyncio.subprocess.PIPE)
            self._output, self._err = await self._process.communicate()

            return self._output, self._err, self._process.returncode
        except Exception as err:
            self._err = "AsyncioSubProcess Error: " + str(err)
            self._output = ""
            return self._output, self._err, self._process.returncode
