import errno
from cortx.utils.log import Log
from cortx.utils.cli.errors import ArgumentError
from cortx.utils.cli.cli_validators import CommonValidators
from csm.core.controllers.validators import BucketNameValidator

class Validators(CommonValidators):

    """CLI Validators Class"""
    @staticmethod
    def bucket_name(value):
        validator = BucketNameValidator()
        if not validator.is_value_valid(value):
            raise ArgumentError(errno.EINVAL,
                ("Bucket Name should be between 4-56 Characters long. "
                 "Should contain either lowercase, numeric or '-' characters. "
                 "Not starting or ending with '-'"))
        return str(value)
