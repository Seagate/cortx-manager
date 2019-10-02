from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Any
from csm.core.blogic.data_access.errors import MalformedQueryError


class IFilterQuery(ABC):
    @abstractmethod
    def accept_visitor(self, visitor) -> Any:
        pass


class FilterOperationAnd(IFilterQuery):
    """
    Class representing AND condition
    :param *args: List of nested filter conditions (each must be of type IFilterQuery)
    """
    def __init__(self, *args):
        if len(args) < 2 or not all(isinstance(x, IFilterQuery) for x in args):
            raise MalformedQueryError("AND operation takes >= 2 arguments of filter type")

        self._operands = args

    def accept_visitor(self, visitor):
        return visitor.handle_and(self)

    def get_operands(self) -> List[IFilterQuery]:
        return self._operands


class FilterOperationOr(IFilterQuery):
    """
    Class representing OR condition
    :param *args: List of nested filter conditions (each must be of type IFilterQuery)
    """
    def __init__(self, *args):
        if len(args) < 2 or not all(isinstance(x, IFilterQuery) for x in args):
            raise MalformedQueryError("OR operation takes >= 2 arguments of filter type")

        self._operands = args

    def accept_visitor(self, visitor):
        return visitor.handle_or(self)

    def get_operands(self) -> List[IFilterQuery]:
        return self._operands


class ComparisonOperation(Enum):
    """
    Enumeration that represents possible comparison operations
    """
    OPERATION_GT = '>'
    OPERATION_LT = '<'
    OPERATION_EQ = '='
    OPERATION_LEQ = '<='
    OPERATION_GEQ = '>='

    @classmethod
    def from_standard_representation(cls, op: str):
        mapping = {
            '=': cls.OPERATION_EQ,
            '>': cls.OPERATION_GT,
            '<': cls.OPERATION_LT,
            '>=': cls.OPERATION_GEQ,
            '<=': cls.OPERATION_LEQ
        }

        if op in mapping:
            return mapping[op]
        else:
            raise MalformedQueryError("Invalid comparison operation: {}".format(op))


class FilterOperationCompare(IFilterQuery):
    """
    Class representing a comparison operation.
    """
    def __init__(self, left_operand, operation: ComparisonOperation, right_operand):
        self.left_operand = left_operand
        self.operation = operation
        self.right_operand = right_operand

    def accept_visitor(self, visitor):
        return visitor.handle_compare(self)

    def get_left_operand(self):
        return self.left_operand

    def get_right_operand(self):
        return self.right_operand

    def get_operation(self) -> ComparisonOperation:
        return self.operation


class IFilterTreeVisitor(ABC):
    """
    Descendants of this class are supposed to be used for filter tree traversal.
    Application of "visitor" design pattern allows to:
    1) Avoid switch'ing over possible filter types
    2) Not to forget to add handers for new filter types as they are added to the system
    """

    @abstractmethod
    def handle_and(self, entry: FilterOperationAnd):
        pass

    @abstractmethod
    def handle_or(self, entry: FilterOperationOr):
        pass

    @abstractmethod
    def handle_compare(self, entry: FilterOperationCompare):
        pass


def And(*args):
    """
    Adds a condition that demands that all the nested conditions are satisfied.
    :param *args: List of nested conditions (each must be an instance of IFilterQuery)
    :returns: a FilterOperationAnd object
    """
    return FilterOperationAnd(*args)


def Or(*args):
    """
    Adds a condition that demands that at least one of the nested conditions is true.
    :param args: List of nested conditions (each must be an instance of IFilterQuery)
    :returns: a FilterOperationOr object
    """
    return FilterOperationOr(*args)


def Compare(left, operation: str, right):
    """
    Adds a condition that demands some order relation between two items.
    :param left: Left operand. Either a field or a value.
    :param operation: a string corresponding to the required operation, e.g. '=' or '>'
    :param right: Right operand. Either a field or a value.
    :returns: a FilterOperationCompare object
    """
    op = ComparisonOperation.from_standard_representation(operation)
    return FilterOperationCompare(left, op, right)
