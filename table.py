##
#   Copyright 2013 Chad Spratt
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
##
import sqlite3
from collections import OrderedDict


class Table(object):
    """Used to open, read and write all files of all supported types."""
    def __init__(self, filename, tablename=None):
        self.filename = filename
        self.tablename = tablename
        self.sqlname = None
        # fields[fieldname] = Field
        self.fields = OrderedDict()

    # this is done separately so that joins can be set up and the fields can
    # be edited without waiting on the sqlite conversion
    def initfields(self):
        print 'init fields==========='
        for field in self.getfields():
            print 'field:', field.originalname
            # cast originalname to str in case it's a unicode str
            self.fields[str(field.originalname)] = field

    # long-running, should yield periodically so the GUI can function
    def convertdata(self, alias):
        """Read the contents of a data file in to an SQLite table."""
        self.sqlname = 'table_' + alias
        # make a list of the field names with type, for creating the table
        fieldnameswithtype = []
        # finish setting up the fields that were added by initfields()
        for fieldname in self.fields:
            field = self.fields[fieldname]
            # cast originalname to str in case it's a unicode str
            field.sqlname = alias + '_' + fieldname
            fieldnameswithtype.append(field.sqlname + ' ' + field['type'])

        # create a string of question marks for the queries
        # one question mark for each field. four fields = '?, ?, ?, ?'
        qmarklist = []
        for _counter in range(len(self.fields)):
            qmarklist.append('?')
        qmarks = ', '.join(qmarklist)

        # open the database
        with sqlite3.connect('temp.db') as conn:
            cur = conn.cursor()
            # create the table
            print ('query: CREATE TABLE ' + self.sqlname + ' (' +
                        ', '.join(fieldnameswithtype) + ')')
            cur.execute('CREATE TABLE ' + self.sqlname + ' (' +
                        ', '.join(fieldnameswithtype) + ')')
            recordcount = self.getrecordcount()
            i = 0
            insertquery = ('INSERT INTO ' + self.sqlname +
                           ' VALUES (' + qmarks + ');')
            # insert each record from the input file
            for record in self:
                values = [record[fn] for fn in self.fields]
                cur.execute(insertquery, values)
                i += 1
                # Take a break so the gui can be used
                if i % 250 == 0:
                    if recordcount is None:
                        yield 'pulse'
                    else:
                        yield float(i) / recordcount
            conn.commit()

    def buildindex(self, indexfield):
        """Create an index for a given field."""
        # open the database
        with sqlite3.connect('temp.db') as conn:
            cur = conn.cursor()
            query = ('CREATE INDEX IF NOT EXISTS ' + indexfield.sqlname +
                     '_index ON ' + self.sqlname + '(' + indexfield.sqlname +
                     ')')
            print query
            cur.execute(query)

    # XXX call getattributeorder() instead?
    def getattributenames(self):
        return self.fieldattrorder


class NeedTableError(Exception):
    def __init__(self, tablelist):
        self.tablelist = tablelist


class InvalidDataError(Exception):
    def __init__(self):
        pass

class TableExistsError(Exception):
    def __init__(self):
        pass