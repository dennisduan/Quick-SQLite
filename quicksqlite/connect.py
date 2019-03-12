import sqlite3, time, logging, re
from .errors import ListenError, ConnectError, DBError

log = logging.getLogger(__name__)

class Connection():
    def __init__(self, path: str=":memory:", auto_commit: bool=True, reconnects: int=3, auto_connect=False, timeout=5):
        self.reconnects = reconnects
        self.path = path
        self.auto_commit = auto_commit
        self.auto_connect = auto_connect
        self.timeout = timeout

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

        self._create_connection()

    def _create_connection(self):
        try:
            self._con = sqlite3.connect(self.path)

            self._handler = self._con.cursor()
            self._dispatch_listener("connect", self.path)

            log.info("Successfully connected to %s" % self.path)
        
        except sqlite3.DatabaseError:
            self._attempt_reconnect()
            
            self._con = None

    def _attempt_reconnect(self, error_on_fail=False):
        for i in range(self.reconnects):
            log.info("Attempting to reconnect to %s on attempt %s" % (self.path, i+1))

            try:
                self._con = sqlite3.connect(self.path)

                self._dispatch_listener("reconnect", self.path, i+1)
                self._handler = self._con.cursor()

                log.info("Reconnected %s after %s attempts." % (self.path, i+1))

                break
        
            except sqlite3.DatabaseError:
                log.info("Failed to connect to %s on attempt %s" % (self.path, i+1))

                if i == self.reconnects - 1:
                    self._dispatch_listener("disconnect", self.path)

                    if error_on_fail:
                        log.error("Connection to the %s failed %s times." % (self.path, self.reconnects))

                        return ConnectError("Connection to the %s failed %s times." % (self.path, self.reconnects))

                pass

            time.sleep(self.reconnects)

    def _handle_locked(self, func, *args, **kwargs):
        time.sleep(self.timeout)
        func(*args, **kwargs)

    def listen(self, func, name=None):
        try:
            if name is None:
                name = func.__name__[3:]

            if name is not None:
                if name.startswith("on_"):
                    name = name[3:]
                
            self._cache["listeners"][name] = func

        except NameError:
            return ListenError("That event couldn't be recognised")

    def _dispatch_listener(self, listener, *args, **kwargs):
        def wrapper():
            try:
                return self._cache["listeners"][listener](*args, **kwargs)
            
            except TypeError:
                return
        
        return wrapper()

    def _check_integrity(self):
        if self._con is not None:
            return

        else:
            self._attempt_reconnect(error_on_fail=True)

    def connect(self):
        if self.auto_connect:
            return

        self._create_connection()

    def close(self):
        self._dispatch_listener("disconnect", self.path)

        self._con.close()
        self._con = None

    def rollback(self):
        self._dispatch_listener("rollback", self.path)
        self._dispatch_listener("transaction_success", self.path, "rollback")

        self._con.rollback()

    def commit(self):
        if self.auto_commit:
            return

        self._dispatch_listener("commit", self.path)
        self._dispatch_listener("transaction_success", self.path, "commit")

        self._con.commit()

    def create_table(self, table_name: str, values: list, types: list):
        self._check_integrity()

        if len(values) != len(types):
            if len(values) == 0 and len(types) == 0:
                return DBError("Insufficient number of values and types.")
                
            return DBError("Insufficient number of %s." % ("values" if len(values) < len(types) else "types"))

        y = 0
        for x in types:
            if x.lower() == "none":
                types[y] = "NULL"

            if x.lower() == "bytes":
                types[y] == "BLOB"
            
            if x.lower() == "int":
                types[y] == "INTEGER"

            if x.lower() == "str":
                types[y] == "TEXT"

            if x.lower() == "float":
                types[y] == "REAL"

            y += 1

            if x.upper() not in ("TEXT", "REAL", "INTEGER", "NULL", "BLOB", "INT", "STR", "BYTES", "NONE", "FLOAT"):
                return DBError("Incorrect type provided. '%s' is not a valid data type." % x.capitalize())

        i = 0
        for x in values:
            values.remove(x)
            values.insert(i, f"{x} {types[i]}")

        try:
            self._handler.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(reversed([x.upper() for x in values]))})")
        
        except Exception as e:
            if re.search("database is locked", e, re.IGNORECASE):
                self._handle_locked(self.create_table, table_name, values, types)

            return DBError(e)

    def drop_table(self, table_name: str):
        self._check_integrity()

        try:
            self._handler.execute(f"DROP TABLE {table_name}")
        
        except Exception as e:
            if re.search("database is locked", e, re.IGNORECASE):
                self._handle_locked(self.drop_table, table_name)

            return DBError(e)

    def insert(self, table: str, values):
        self._check_integrity()

        ques = ", ".join([f"'{x}'" for x in values])

        try:
            self._handler.execute(f"INSERT INTO {table} VALUES ({ques})")

        except Exception as e:
            if re.search("database is locked", e, re.IGNORECASE):
                self._handle_locked(self.insert, table, values)

            return DBError(e)

        if self.auto_commit:
            self._con.commit()

        self._dispatch_listener("transaction_success", self.path, "insert")

    def delete(self, table: str, column_w: str=None, value_w: str=None):
        self._check_integrity()

        if column_w is None and value_w is not None:
            return DBError("'value_w' and 'column_w' must both be None or a str")

        if column_w is not None and value_w is not None:
            ques = f"WHERE {column_w}=?"

        try:
            if column_w is None and value_w is None:
                self._handler.execute(f"DELETE FROM {table}")

            else:
                self._handler.execute(f"DELETE FROM {table} {ques}", (value_w,))
        
        except Exception as e:
            if re.search("database is locked", e, re.IGNORECASE):
                self._handle_locked(self.delete, table, column_w, value_w)

            return DBError(e)

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
            if re.search("database is locked", e, re.IGNORECASE):
                self._handle_locked(self.update, table, column, value, column_w, value_w)

            return DBError(e)

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
            if re.search("database is locked", e, re.IGNORECASE):
                self._handle_locked(self.select, table, select, column_w, value_w, fetchall, limit, random)

            return DBError(e)

        if self.auto_commit:
            self._con.commit()

        self._dispatch_listener("transaction_success", self.path, "select")

        return data

