"""
 ****************************************************************************
 Filename:          usl_access_parameters_schema.py
 Description:       USL access parameters schema.

 Creation Date:     03/03/2020
 Author:            Tadeu Bastos

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

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
