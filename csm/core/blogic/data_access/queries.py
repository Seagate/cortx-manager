
class Query:

    """Storage Query API"""

    def __init__(self):
        pass

    def order_by(self):
        pass

    def group_by(self):
        pass

    def filter_by(self):
        pass

    def limit(self):
        pass

    def having(self):
        pass

    def offset(self):
        pass


class ExtQuery(Query):

    """Storage Extended Query API used by Storage aggregation functions"""

    def __init__(self):
        super().__init__()

