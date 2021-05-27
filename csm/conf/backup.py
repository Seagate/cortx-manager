from csm.core.providers.providers import Response
from csm.core.blogic import const
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.log import Log


class Backup(Setup):
    """
    Perform backup for csm
    """
    def __init__(self):
        super(Backup, self).__init__()

    async def execute(self, command):
        Log.info("Perform backup for csm_setup")
        # TODO: Implement backup logic 
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)