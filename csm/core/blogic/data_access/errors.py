
from csm.common.errors import CsmInternalError


class DataAccessError(CsmInternalError):

    """Base Data Access Error"""


class DataAccessExternalError(DataAccessError):

    """Internal DB errors which happen outside of CSM"""


class DataAccessInternalError(DataAccessError):

    """Errors regarding CSM part of Data Access implementation"""


class MalformedQueryError(DataAccessError):

    """Malformed Query or Filter error"""


class MalformedConfigurationError(DataAccessError):

    """Error in configuration of data bases or storages or db drivers"""


class StorageNotFoundError(DataAccessError):

    """Model object is not associated with any storage"""
