#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          process.py
 Description:       Execute process and provide output.

 Creation Date:     09/09/2019
 Author:            Ajay Paratmandali

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import subprocess
import asyncio

class Process:
    def __init__(self, cmd):
        self._cmd = cmd
        pass

    def run(self):
        pass

class SimpleProcess(Process):
    ''' Execute process and provide output '''
    def __init__(self, cmd):
        super(SimpleProcess, self).__init__(cmd)
        self.shell=False
        self.cwd=None
        self.timeout=None
        self.env=None
        self.universal_newlines=None

    def run(self, **args):
        ''' This will can run simple process '''
        for key, value in args.items():
            setattr(self, key, value)

        try:
            cmd = self._cmd.split() if type(self._cmd) is str else self._cmd
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
    ''' Execute process with pipe and provide output '''
    def __init__(self, cmd):
        super(PipedProcess, self).__init__(cmd)

    def run(self, **args):
        #TODO
        pass

class AsyncioSubprocess(Process):
    def __init__(self, cmd):
        super(AsyncioSubprocess, self).__init__(cmd)
        
    async def run(self, **agrs):
        try:
            self._process = await asyncio.create_subprocess_shell(self._cmd, 
                                                            stdout=asyncio.subprocess.PIPE, 
                                                            stderr=asyncio.subprocess.PIPE)
            self._output, self._err = await self._process.communicate()

            return self._output, self._err
        except Exception as err:
            self._err = "AsyncioSubProcess Error: " + str(err)
            self._output = ""
            return self._output, self._err