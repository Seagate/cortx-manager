from schematics.models import Model

from csm.common.errors import CsmInternalError


PRIMARY_KEY_FIELD = "_id"


class PrimaryKey:

    def __init__(self, model_id=None):
        self._id = PRIMARY_KEY_FIELD if model_id is None else model_id

    def __get__(self, instance, owner):
        if instance is None:
            # It means that this method is called from class itself
            return getattr(owner, self._id)

        return getattr(instance, self._id)

    def __set__(self, instance, value):
        if instance is None:
            raise CsmInternalError("'__set__' method is called when instance is None")
        setattr(instance, self._id, value)


class PrimaryKeyValue:

    def __init__(self, model_id=None):
        self._id = PRIMARY_KEY_FIELD if model_id is None else model_id

    def __get__(self, instance, owner):
        if instance is None:
            primary_key_field = getattr(owner, self._id)
            return getattr(owner, primary_key_field)

        primary_key_field = getattr(instance, self._id)
        return getattr(instance, primary_key_field)

    def __set__(self, instance, value):
        if instance is None:
            raise CsmInternalError("'__set__' method is called when instance is None")

        primary_key_field = getattr(instance, self._id)
        setattr(instance, primary_key_field, value)


class CsmModel(Model):

    """
    Base model
    """

    _id = None  # This field used as Primary key of the Model
    primary_key = PrimaryKey()
    primary_key_val = PrimaryKeyValue()

    # TODO: based on primary key we can define compare operations for CsmModel instances
    # TODO: based on primary key we can define hashing of CsmModel instances
