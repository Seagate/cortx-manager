# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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

from enum import Enum
class RgwConnectionConfig:
    """Configuration options for RGW connection."""

    host: str
    port: int
    auth_user: str
    auth_user_access_key: str
    auth_user_secret_key: str

class RgwErrors(Enum):
    """Enum with error responses."""

    # Standard error responses
    AccessDenied = "Access denied."
    InternalError = "Internal server error."
    NoSuchUser = "User does not exist."
    NoSuchBucket = "Bucket does not exist."
    NoSuchKey = "No such access key."
    SignatureDoesNotMatch = "Signature Does Not Match."
    UnknownError = "Unknown Error from S3 service."
    # Create user error responses
    UserAlreadyExists = "Attempt to create existing user."
    InvalidAccessKeyId = "Invalid access key specified."
    InvalidKeyType = "Invalid key type specified."
    InvalidSecretKey = "Invalid secret key specified."
    KeyExists = "Provided access key exists and belongs to another user."
    EmailExists = "Provided email address exists."
    InvalidCapability = "Attempt to grant invalid admin capability."

class RgwError:
    """Class that describes a non-successful result"""

    http_status: int
    error_code: RgwErrors
    error_message: str
