import sqlite3, time
from .errors import ListenError, ConnectError, OptionError

class Connection():
    def __init__(self, path: str=":memory:", auto_commit: bool=True, reconnects: int=3, auto_connect=False):
        self.reconnects = reconnects
        self.path = path
        self.auto_commit = auto_commit
        self.auto_connect = auto_connect

        self._cache = {
            "listeners": {
                "reconnect": None,
                "connect": None,
                "disconnect": None,
                "error": None,
                "transaction_success": None,
                "rollback": None,
                "commit": None
            }
        }

        if self.auto_commit:
            self.commit = None

        if auto_connect:
            try:
                self._con = sqlite3.connect(path)

                # The connection was successful, open up a handler and dispatch the connect listener
                self._handler = self._con.cursor()
                self._dispatch_listener("connect", self.path)
            
            # The initial connection failed, hand control over to the reconnection handler
            except sqlite3.DatabaseError:
                self._attempt_reconnect()
                
                self._con = None

            self.connect = None

    def _attempt_reconnect(self, error_on_fail=False):
        for i in range(self.reconnects):
            try:
                self._con = sqlite3.connect(self.path)

                # The connection was successful, dispatch the reconnect listener and set the handler's connection
                self._dispatch_listener("reconnect", self.path, i+1)
                self._handler = self._con.cursor()
                break
        
            # The connection failed, calmly process the error
            except sqlite3.DatabaseError:

                # We've ran out of reconnects, dispatch the disconnect listener
                if i == self.reconnects - 1:
                    self._dispatch_listener("disconnect", self.path)

                    if error_on_fail:
                        raise ConnectError("Connection to the database failed 3 times")

                pass

            time.sleep(1 + (self.reconnects - 1))

    def listen(self, func):
        try:
            self._cache["listeners"][func.__name__[3:]] = func

        # The event isn't supported, send a custom, parsable exception
        except NameError:
            raise ListenError("That event couldn't be recognised")

    def _dispatch_listener(self, listener, *args, **kwargs):
        def wrapper():
            try:
                return self._cache["listeners"][listener](*args, **kwargs)
            
            # The listener isn't in cache, silently pass
            except NameError:
                return False
            except TypeError:
                return False
        
        return wrapper()

    def _check_integrity(self):
        if self._con is not None:
            return True

        # We can't find a connection, attempt to make a reconnection
        else:
            self._attempt_reconnect(error_on_fail=True)
            return False

    def connect(self):
        try:
            self._con = sqlite3.connect(self.path)

            # The connection was successful, open up a handler and dispatch the connect listener
            self._handler = self._con.cursor()
            self._dispatch_listener("connect", self.path)
        
        # The initial connection failed, hand control over to the reconnection handler
        except sqlite3.DatabaseError:
            self._attempt_reconnect()
            
            self._con = None

    def close(self):
        self._dispatch_listener("disconnect", self.path)

        self._con.close()
        self._con = None

    def rollback(self):
        self._dispatch_listener("rollback", self.path)
        self._dispatch_listener("transaction_success", self.path, "rollback")

        self._con.rollback()

    def commit(self):
        self._dispatch_listener("commit", self.path)
        self._dispatch_listener("transaction_success", self.path, "commit")

        self._con.commit()

    def create_table(self, table_name: str, values: list, types: list):
        self._check_integrity()

        if len(values) != len(types):
            raise OptionError("The number of provided values should be the same as the number of provided types")

        i = 0
        for x in values:
            values.remove(x)
            values.insert(i, f"{x} {types[i]}")

        try:
            self._handler.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(reversed(values))})")
        
        except Exception as e:
            raise OptionError(e)

    def drop_table(self, table_name: str):
        self._check_integrity()

        try:
            self._handler.execute(f"DROP TABLE {table_name}")
        
        except Exception as e:
            raise OptionError(e)

    def insert(self, table: str, values):
        self._check_integrity()

        ques = ", ".join([f"'{x}'" for x in values])

        try:
            self._handler.execute(f"INSERT INTO {table} VALUES ({ques})")
        except Exception as e:
            raise OptionError(e)

        if self.auto_commit:
            self._con.commit()

        self._dispatch_listener("transaction_success", self.path, "insert")

    def delete(self, table: str, column_w: str=None, value_w: str=None):
        self._check_integrity()

        if column_w is None and value_w is not None:
            raise OptionError("'value_w' and 'column_w' must both be None or a str")

        if column_w is not None and value_w is not None:
            ques = f"WHERE {column_w}=?"

        try:
            if column_w is None and value_w is None:
                self._handler.execute(f"DELETE FROM {table}")

            else:
                self._handler.execute(f"DELETE FROM {table} {ques}", (value_w,))
        
        except Exception as e:
            raise OptionError(e)

        if self.auto_commit:
            self._con.commit()

        self._dispatch_listener("transaction_success", self.path, "delete")

    def update(self, table: str, column, value, column_w: str=None, value_w: str=None):
        self._check_integrity()

        try:
            if column_w is not None and value_w is not None:
                self._handler.execute(f"UPDATE {table} SET {column}=? WHERE {column_w}=?", (value, value_w))

            else:
                self._handler.execute(f"UPDATE {table} SET {column}=?", (value,))
        
        except Exception as e:
            raise OptionError(e)

        if self.auto_commit:
            self._con.commit()

        self._dispatch_listener("transaction_success", self.path, "update")

    def select(self, table: str, select, column_w: str=None, value_w: str=None, fetchall=False, limit=None, random=False):
        self._check_integrity()

        if not isinstance(select, (tuple, list)):
            select = (select,)

        if limit is not None:
            limit = f" LIMIT {limit}"
        if limit is None:
            limit = ""

        if not random:
            random = ""
        if random:
            random = " ORDER BY RANDOM()"

        try:
            if column_w is not None and value_w is not None:
                if not fetchall:
                    data = self._handler.execute(f"SELECT {', '.join(select)} FROM {table} WHERE {column_w}=? {random}{limit}", (value_w,)).fetchone()
                
                else:
                    data = self._handler.execute(f"SELECT {', '.join(select)} FROM {table} WHERE {column_w}=? {random}{limit}", (value_w,)).fetchall()

            if column_w is None and value_w is None:
                if not fetchall:
                    data = self._handler.execute(f"SELECT {', '.join(select)} FROM {table}{random}{limit}").fetchone()
                
                else:
                    data = self._handler.execute(f"SELECT {', '.join(select)} FROM {table}{random}{limit}").fetchall()
        
        except Exception as e:
            raise OptionError(e)

        if self.auto_commit:
            self._con.commit()

        self._dispatch_listener("transaction_success", self.path, "select")

        return data
