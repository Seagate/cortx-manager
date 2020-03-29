#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          validators.py
 Description:       This File will serve as Command Validators for CSM

 Creation Date:     20/11/2019
 Author:            Prathamesh Rodi

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import re
from marshmallow.validate import Validator, ValidationError
from csm.core.blogic import const
from csm.core.services.file_transfer import FileRef


class FileRefValidator(Validator):
    """
    Validator Class for check FileRef instance
    """

    def __call__(self, value):
        if not isinstance(value, FileRef):
            raise ValidationError('This field must be of instance of a FileRef class')



class UserNameValidator(Validator):
    """
    Validator Class for Username Fields in CSM
    """

    def __call__(self, value):
        if not re.search(r"^[a-zA-Z0-9_-]{4,56}$", value):
            raise ValidationError(
                "Username can only contain Alphanumeric, - and  _ .Length "
                "Must be between 4-64 Characters")


class CommentsValidator(Validator):
    """
    Validation Class for Comments and Strings in CSM
    """

    def __call__(self, value):
        if len(value) > const.STRING_MAX_VALUE:
            raise ValidationError(
                "Length should not be more than that of 250 characters.")


class PortValidator(Validator):
    """
    Validation Class for Ports Entered in CSM
    """

    def __call__(self, value):
        if not const.PORT_MIN_VALUE < int(value) or not const.PORT_MAX_VALUE > int(value):
            raise ValidationError(f"Port Value should be between {const.PORT_MIN_VALUE} than {const.PORT_MAX_VALUE}")


class PathPrefixValidator(Validator):
    """
    Path Prefix Validator for S3 Paths.
    """

    def __call__(self, value):
        if len(value) > const.PATH_PREFIX_MAX_VALUE:
            raise ValidationError(f"Path must not be more than {const.PATH_PREFIX_MAX_VALUE} characters.")
        if not value.startswith("/"):
            raise ValidationError("Path Must Start with '/'.")


class PasswordValidator(Validator):
    """
    Password Validator Class for CSM Passwords Fields.
    """

    def __call__(self, password):
        error = []
        if len(password) < 8:
             error.append("Must be more than 8 characters.")
        if not any(each_char.isupper() for each_char in password):
            error.append("Must contain at least one Uppercase Alphabet.")
        if not any(each_char.islower() for each_char in password):
            error.append("Must contain at least one Lowercase Alphabet.")
        if not any(each_char.isdigit() for each_char in password):
            error.append("Must contain at least one Numeric value.")
        if not any(each_char in const.PASSWORD_SPECIAL_CHARACTER
                   for each_char in password):
            error.append(f"Must include {''.join(const.PASSWORD_SPECIAL_CHARACTER)}.")
        if error:
            error_str = "\n".join(error)
            raise ValidationError(f"Password Policy Not Met.\n{error_str}")


class BucketNameValidator(Validator):
    """
        Validator Class for Bucket Name.
    """

    def is_value_valid(self, value):
        return re.search(r"^[a-z0-9][a-z0-9-]{3,54}[a-z0-9]$", value)

    def __call__(self, value):
        if not self.is_value_valid(value):
            raise ValidationError(
                ("Bucket Name should be between 4-56 Characters long."
                 "Should contain either lowercase, numeric or '-' characters. "
                 "Not starting or ending with '-'"))


class Ipv4(Validator):
    """
    Validator class for ipv4 address validation.
    """

    @staticmethod
    def validate_ipv4(ip):
        ip_regex = ("^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.("
                    "25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.("
                    "25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.("
                    "25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$")
        return re.search(ip_regex, ip)

    def __call__(self, ip):
        if not self.validate_ipv4(ip):
            raise ValidationError(
                "Invalid IP4 address.")


class DomainName(Validator):
    """
    Validator class for domain name validation.
    """

    @staticmethod
    def validate_domain_name(domain_name):
        domain_regex = "^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,6}$"
        return re.search(domain_regex, domain_name)

    def __call__(self, domain_name):
        if len(domain_name) > 253:
            raise ValidationError(
                "Domain name should be less than 253 characters")
        if not self.validate_domain_name(domain_name):
            raise ValidationError(
                "Invalid domain name.")


class Server(Validator):
    """
    Validator class for both ipv4 address and domain name validation.
    """

    def __call__(self, server_name):
        if len(server_name) > 253:
            raise ValidationError(
                "Server name should be less than 253 characters")
        if not (Ipv4.validate_ipv4(server_name) or
                DomainName.validate_domain_name(server_name)):
            raise ValidationError(
                "Invalid server name.")

class Enum(Validator):
    def __init__(self, validator_values):
        self._validator_values = validator_values
    def __call__(self, value):
        if value not in self._validator_values:
            raise ValidationError(
                f"Incorrect Value: Should be from {' '.join(self._validator_values)}"
            )

class ValidationErrorFormatter:
    @staticmethod
    def format(validation_error_obj: ValidationError) -> str:
        """
        This Method will Format Validation Error messages to Proper Error messages.
        :param validation_error_obj: Validation Error Object :type: ValidationError
        :return: String for all Validation Error Messages
        """
        error_messages = []
        for each_key in validation_error_obj.messages.keys():
            error_messages.append(f"{each_key.capitalize()}: {''.join(validation_error_obj.messages[each_key])}")
        return "\n".join(error_messages)


class IsoFilenameValidator(Validator):
    """
    Validator class for validating firmware and hotfix package file name.
    """

    def __call__(self, file_name):
        if not file_name.endswith(".iso"):
            raise ValidationError("Package should be a '.iso' file.")
