import MySQLdb

import types

from baseball.simulator import utils

logger = utils.setup_logger('query_logger', 'logs/queries.log')


def connect(*args, **kwargs):
    return DB(*args, **kwargs)


class DB:
    def __init__(self, *args, **kwargs):
        self.db = MySQLdb.connect(*args, **kwargs)

    def cursor(self):
        """
        Returns the query wrapper to self.cur.execute
        So that the queries can be logged
        """
        cursor = self.db.cursor()
        cursor._execute = cursor.execute

        def execute(self, sql_query):
            logger.info(" execute: %s" % sql_query)
            self._execute(sql_query)
        cursor.execute = types.MethodType(execute, cursor)
        return cursor
