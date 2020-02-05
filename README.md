# Quick-SQLite

<div>
  <p>
    <a href="https://www.patreon.com/join/JackTEK?" data-patreon-widget-type="become-patron-button"><img src="https://c5.patreon.com/external/logo/become_a_patron_button@2x.png" width="85"></a>
    <a href="https://discord.gg/gDcqBJJ"><img src="https://discordapp.com/api/guilds/499602039232397343/embed.png" alt="Discord Server" /></a>
    <a href="https://GitHub.com/MilaBot/Quick-SQLite/stargazers/"><img src="https://img.shields.io/github/stars/MilaBot/Quick-SQLite.svg?style=social&label=Star"></a>
  </p>
    

| Documentation | Discord Support | PyPI Page | Dependants |
| :---: | :---: | :---: | :---: |
| [quick-sqlite.milabot.xyz](https://quick-sqlite.milabot.xyz) | [discord.gg/gDcqBJJ](https://discord.gg/gDcqBJJ) | [pypi.org/project/quick-sqlite](https://pypi.org/project/quick-sqlite) | [github.com/MilaBot/Quick-SQLite/network/dependents](https://github.com/MilaBot/Quick-SQLite/network/dependents)

</div>

___

- Data is persistent and file-stored
- Designed to be easy & clean to use by anyone
- [Discord Support](https://discord.gg/gDcqBJJ)
- Supports the entire SQL API
- Built with event listeners for monitoring

---

## Introduction

Quick-SQLite is intended for programmers that dislike the unattractive and needlessly extensive SQLite3 API. Quick-SQLite not only reduces the ugly-looking function set with a clean and organised function set, but it also comes with many useful settings such as auto-commiting, automatic reconnecting, and event listeners. The integrated events listeners - demonstrated later on - are functions inside your script that are called every time something specific happens, for example, the disconnect listener is called everytime the connection disconnects, more on that later.

## Installation

To install Quick-SQLite, just run the following command:

> *pip install quick-sqlite*

## Comparison

### SQLite3

```python
from sqlite3 import connect

with connect("Database.db") as c:
    data = c.cursor().execute("SELECT Z FROM Table WHERE X=?", ("Y",)).fetchone()[0]
    c.cursor().execute("UPDATE Table SET X=? WHERE X=?", ("Y", f"{data}Y"))
    c.commit()
```

### Quick-SQLite

```python
from quicksqlite import Connection

c = Connection(path="Database.db", auto_connect=True)
c.update("Table", "X", f"{c.select('Table', 'Z', column_w='X', value_w='Y')[0]}Y")
```

## Examples

### Minimal Usage

```python
from quicksqlite import Connection

# Define our connection instance
con = Connection(path="Database.db", auto_commit=False, reconnects=5, auto_connect=True)

# Create table
con.create_table("Employees", ["Name", "Age", "Salary"], ["TEXT", "INTEGER", "REAL"])

# Insert row
con.insert("Employees", ["Andrew Anderson", 32, 100.00])

# Update row
con.update("Employees", "Salary", 110.00, column_w="Name", value_w="Andrew Anderson")

# Select row
print(con.select("Employees", "Age", column_w="Name", value_w="Andrew Anderson", fetchall=False, random=False, limit=1))

# Delete row
con.delete("Employees", column_w="Name", value_w="Andrew Anderson")

# Drop table
con.drop_table("Employees")

# Commit changes
con.commit()

# Rollback
con.rollback()

# Close the connection
con.close()
```

### Using listeners

```python
from quicksqlite import Connection

# Define our connection instance
con = Connection(path="Database.db", auto_commit=True, reconnects=5)

@con.listen
def on_connect(db):
    print(f"Connected to {db}")

@con.listen
def on_disconnect(db):
    print(f"Disconnected from {db}")

@con.listen
def on_reconnect(db, attempt_number):
    print(f"Reconnected from {db} on attempt number {attempt_number}")

@con.listen
def on_transaction_success(db, action):
    print(f"A transaction was completed in {db}, the action was {action}")

@con.listen
def on_rollback(db):
    print(f"The last commit to {db} has been rolled back")

@con.listen
def on_commit(db):
    print(f"Changes to {db} have been saved")

# Create table
con.create_table("Employees", ["Name", "Age", "Salary"], ["TEXT", "INTEGER", "REAL"])

# Insert row
con.insert("Employees", ["Andrew Anderson", 32, 100.00])

# Update row
con.update("Employees", "Salary", 110.00, column_w="Name", value_w="Andrew Anderson")

# Select row
print(con.select("Employees", "Age", column_w="Name", value="Andrew Anderson", fetchall=False, random=False, limit=1))

# Delete row
con.delete("Employees", column_w="Name", value_w="Andrew Anderson")

# Drop table
con.drop_table("Employees")

# Rollback
con.rollback()

# Close the connection
con.close()
```

### In-class Example

```python
from quicksqlite import Connection

class MyClass(Connection):
    def __init__(self):
        # Define our connection instance
        super().__init__(path="Database.db", auto_commit=True, reconnects=5)
        
        # Setup listeners
        self.listen(self.some_function, name="connect")
        self.listen(self.on_disconnect)
        self.listen(self.on_reconnect)
        self.listen(self.on_success)
        self.listen(self.on_rollback)
        self.listen(self.on_commit)

    def some_function(self, db):
        print(f"Connected to {db}")

    def on_disconnect(self, db):
        print(f"Disconnected from {db}")

    def on_reconnect(self, db, attempt_number):
        print(f"Reconnected from {db} on attempt number {attempt_number}")

    def on_success(self, db, action):
        print(f"A transaction was completed in {db}, the action was {action}")

    def on_rollback(self, db):
        print(f"The last commit to {db} has been rolled back")

    def on_commit(self, db):
        print(f"Changes to {db} have been saved")

if __name__ == "__main__":
    con = MyClass()

# Functions from the previous examples are used exactly the same as they are here, for example:
con.create_table("Employees", ["Name", "Age", "Salary"], ["TEXT", "INTEGER", "REAL"])

con.close()
```
