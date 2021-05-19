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

import errno
from cortx.utils.log import Log
from cortx.utils.cli_framework.errors import CliError
from cortx.utils.validator.cli_validators import CommonValidators
from csm.core.controllers.validators import BucketNameValidator

class Validators(CommonValidators):

    """CLI Validators Class"""
    @staticmethod
    def bucket_name(value):
        validator = BucketNameValidator()
        if not validator.is_value_valid(value):
            raise CliError(errno.EINVAL,
                ("Bucket Name should be between 4-56 Characters long. "
                 "Should contain either lowercase, numeric or '-' characters. "
                 "Not starting or ending with '-'"))
        return str(value)
