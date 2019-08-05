"""
 ****************************************************************************
 Filename:          provider_factory.py
 Description:       Provider Factory

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

import errno
from csm.core.providers.providers import BundleProvider
from csm.core.providers.providers import EmailProvider
from csm.core.providers.init_provider import InitProvider
from csm.common.errors import CsmError
from csm.common import const

class ProviderFactory(object):
    """ Factory for representing and instantiating providers """

    providers = {
        const.SUPPORT_BUNDLE: BundleProvider,
        const.EMAIL_CONFIGURATION: EmailProvider,
        const.CSM_INIT_CMD: InitProvider
    }

    @staticmethod
    def get_provider(name, cluster):
        """ Returns provider instance corresponding to given name """

        if name not in ProviderFactory.providers:
            raise CsmError(errno.EINVAL, 'Provider %s not loaded' %name)
        return ProviderFactory.providers[name](cluster)
