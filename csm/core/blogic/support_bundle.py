#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          support_bundle.py
 Description:       Contains functionality to create, delete and list
                    support bundles.

 Creation Date:     22/05/2018
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
import os
import errno
from datetime import datetime
import sys
import shutil
import subprocess

from csm.common.cluster import Node, Cluster
from threading import Thread
from csm.common.file_collector import RemoteFileCollector
from csm.common.log import Log
from csm.common.conf import Conf
from csm.core.blogic import const
from csm.common.errors import CsmError


class SupportBundle(object):
    """ Logic to manage support bundles.  """

    def __init__(self, cluster, collection_rules, bundle_root=None):
        self._cluster = cluster
        self._collection_rules = collection_rules
        self._thread_pool = []

        self._bundle_root = bundle_root
        if self._bundle_root is None:
            self._bundle_root = Conf.get(const.SUPPORT_BUNDLE_ROOT, const.DEFAULT_SUPPORT_BUNDLE_ROOT)

    def create(self, bundle_name=None):
        """
        Collect all the logs and other required files for all the components
        """

        try:
            if bundle_name is None or bundle_name == '':
                bundle_name = datetime.now().strftime("%Y%m%d-%H%M%S")
            bundle_path = os.path.join(self._bundle_root, bundle_name)

            if os.path.exists(bundle_path): shutil.rmtree(bundle_path)
            Log.info('Creating support bundle %s.tgz' %bundle_path)

            for node in self._cluster.active_node_list():
                target_path = os.path.join(bundle_path, node.host_name())
                # Initialise file collector.
                file_collector = RemoteFileCollector(self._collection_rules, \
                    node.host_name(), node.admin_user(), target_path)
                thread_id = Thread(target=file_collector.collect, \
                    args=(node.sw_components(),))
                # Register thread in thread pool.
                self._thread_pool.append(thread_id)

            # Start worker thread.
            for thread in self._thread_pool: thread.start()

            # Wait till all worker finishes their task.
            for thread in self._thread_pool: thread.join()

            bundle_cmd = "tar -czf %s.tgz -C %s %s" %(bundle_path, \
                self._bundle_root, bundle_name)
            output = subprocess.check_output(bundle_cmd, stderr=subprocess.PIPE,
                                             shell=True)
            print('Removing %s' %bundle_path)
            shutil.rmtree(bundle_path)
            msg = "Support bundle %s.tgz created." % bundle_path

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' %e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)

        return msg

    def list(self):
        """ Returns list of bundles exist in the repo """
        if not os.path.exists(self._bundle_root):
            return ['No bundle created so far.']

        try:
            output = ['Time\t\tBundle\t\tPath']
            bundle_list = []
            for root, dirs, files in os.walk(self._bundle_root, onerror=self._onerror):
                for f in files:
                    if f.endswith('.tgz'):
                        bundle = os.path.splitext(f)[0]
                        file_path = os.path.join(root, f)
                        time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%y-%m-%d:%H:%M')
                        bundle_list.append('%s\t%0.15s\t%s' %(time, bundle.ljust(15), file_path))
            if len(bundle_list) == 0:
                return ['No bundle created so far.']

            output.extend(bundle_list)

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' %e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)

        return output

    def delete(self, bundle_name):
        """ Deletes a given bundle """

        if os.path.isabs(bundle_name):
            if not bundle_name.startswith(self._bundle_root):
                raise CsmError(errno.EINVAL, 'invalid bundle path')
            bundle_path = bundle_name

        else:
            bundle_file_name = '%s.tgz' % bundle_name
            bundle_path = os.path.join(self._bundle_root, bundle_file_name)

        try:
            if not os.path.exists(bundle_path):
                raise CsmError(errno.EINVAL, 'support bundle "%s" does not exist'
                               %bundle_name)

            Log.info('Deleting support bundle %s.tgz' %bundle_path)
            os.remove(bundle_path)
            msg = "Support bundle %s deleted." % bundle_name

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
