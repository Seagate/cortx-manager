from elasticsearch_dsl import Q
from schematics.models import FieldDescriptor
from csm.core.blogic.filters import IFilterTreeVisitor, \
    FilterOperationAnd, FilterOperationOr, FilterOperationCompare
from csm.core.blogic.filters import ComparisonOperation, IFilterQuery


def _match_query(field: str, target):
    obj = {
        field: target
    }

    return Q("match", **obj)


def _range_generator(op_string: str):
    def _make_query(field: str, target):
        obj = {
            field: {
                op_string: target
            }
        }

        return Q("range", **obj)

    return _make_query


class ElasticSearchQueryConverter(IFilterTreeVisitor):
    """
    Implementation of filter tree visitor that converts the tree into the Query
    object of elasticsearch-dsl library.

    Usage:
    converter = ElasticSearchQueryConverter()
    q_obj = converter.build(filter_root)
    """
    def __init__(self):
        self.comparison_conversion = {
            ComparisonOperation.OPERATION_EQ: _match_query,
            ComparisonOperation.OPERATION_LT: _range_generator('lt'),
            ComparisonOperation.OPERATION_GT: _range_generator('gt'),
            ComparisonOperation.OPERATION_LTE: _range_generator('lte'),
            ComparisonOperation.OPERATION_GTE: _range_generator('gte')
        }

    def build(self, root: IFilterQuery):
        # TODO: may be, we should move this method to the entity that processes
        # Query objects
        return self.accept_visitor(root)

    def handle_and(self, entry: FilterOperationAnd):
        operands = entry.get_operands()
        if len(operands) < 2:
            raise Exception("Malformed AND operation: fewer than two arguments")

        ret = operands[0].accept_visitor(self)
        for operand in operands[1:]:
            ret = ret & operand.accept_visitor(operand)

        return ret

    def handle_or(self, entry: FilterOperationOr):
        operands = entry.get_operands()
        if len(operands) < 2:
            raise Exception("Malformed OR operation: fewer than two arguments")

        ret = operands[0].accept_visitor(self)
        for operand in operands[1:]:
            ret = ret | operand.accept_visitor(operand)

        return ret

    def handle_compare(self, entry: FilterOperationCompare):
        field = entry.get_left_operand()
        field_str = None

        if isinstance(field, str):
            field_str = field
        elif isinstance(field, FieldDescriptor):
            field_str = field.name
        else:
            raise Exception("Failed to process left side of comparison operation")

        op = entry.get_operation()
        return self.comparison_conversion[op](field_str, entry.get_right_operand())
