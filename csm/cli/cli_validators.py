import errno
from csm.common.payload import CommonPayload
from cortx.utils.log import Log
from cortx.utils.cli.errors import ArgumentError
from csm.core.controllers.validators import BucketNameValidator

class Validatiors:
    
    """CLI Validatiors Class"""
    @staticmethod
    def positive_int(value):
        try:
            if int(value) > -1:
                return int(value)
            raise ArgumentError(errno.EINVAL, "Value Must be Positive Integer")
        except ValueError:
            raise ArgumentError(errno.EINVAL,"Value Must be Positive Integer")

    @staticmethod
    def file_parser(value):
        try:
            return CommonPayload(value).load()
        except ValueError as ve:
            Log.error(f"File parsing failed. {value}: {ve}")
            raise ArgumentError(errno.EINVAL,
                ("File operations failed. "
                 "Please check if the file is valid or not"))
        except FileNotFoundError as err:
            Log.error(f"No such file present. {value}: {err}")
            raise ArgumentError(errno.ENOENT,
                ("File operation failed. "
                 "Please check if the file exists."))
        except KeyError as err:
            Log.error(f"Check file type. {value}: {err}")
            raise ArgumentError(errno.ENOENT,
                ("File operation failed. "
                 "Please check if the file exists and its type."))

    @staticmethod
    def bucket_name(value):
        validator = BucketNameValidator()
        if not validator.is_value_valid(value):
            raise ArgumentError(errno.EINVAL,
                ("Bucket Name should be between 4-56 Characters long. "
                 "Should contain either lowercase, numeric or '-' characters. "
                 "Not starting or ending with '-'"))
        return str(value)
