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

from marshmallow import Schema, fields, validates, ValidationError
from typing import Dict, Tuple


class S3CredentialsSchema(Schema):
    access_key = fields.Str(data_key='accessKey', required=True)
    secret_access_key = fields.Str(data_key='secretKey', required=True)


class S3AccessParamsSchema(Schema):
    uri = fields.String(required=True)
    credentials = fields.Nested(S3CredentialsSchema, required=True)

    @validates('uri')
    def validate_uri(self, value: str) -> None:
        if not value.startswith('s3://'):
            raise ValidationError('Invalid S3 URI')


class AccessParamsSchema(Schema):
    """
    USL access parameters schema.

    Required at endpoints that expose S3 services.
    """

    access_params = fields.Nested(S3AccessParamsSchema, data_key='accessParams', required=True)

    @staticmethod
    def flatten(params: Dict) -> Tuple[str, str, str]:
        """
        Flattens the dictionary generated during deserialization.

        :param params: dictionary generated during deserialization
        :return: Tuple with flattened values from ``params``, namely: URI, access key, and secret
            access key.
        """
        return (
            params['access_params']['uri'],
            params['access_params']['credentials']['access_key'],
            params['access_params']['credentials']['secret_access_key'],
        )
