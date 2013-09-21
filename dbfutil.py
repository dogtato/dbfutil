#!/usr/bin/python
"""This utility provides an easy interface for working with database files.

To create a new, empty file, click the refresh button on the middle toolbar to
initialize the list. Then click the + to add fields you can define.

To modify an existing file, load the file, click the refresh button, and then
modify the fields.

To join and modify multiple files, load the files, configure how they will join
together, click refresh to load the fields, then adjust the fields.
"""
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
# callback functions for the gui
import gtk
import time
import random
import sqlite3

import gui
import filemanager
import joinmanager
import outputmanager
import calculator
import table  # for NeedTableError

# event handlers
from gui_files import GUI_Files
from gui_joinconfig import GUI_JoinConfig
from gui_fieldtoolbar import GUI_FieldToolbar
from gui_outputview import GUI_OutputView
from gui_calc import GUI_Calc
from gui_functioneditor import GUI_FunctionEditor
from gui_keyboard import GUI_Keyboard


class DBFUtil(GUI_Files, GUI_JoinConfig, GUI_FieldToolbar, GUI_OutputView,
              GUI_Calc, GUI_FunctionEditor, GUI_Keyboard):

    """Main class, links GUI to the back end and also orchestrates a bit."""

    def __init__(self):
        self.gui = gui.creategui(self)
        self.files = filemanager.FileManager()
        self.joins = joinmanager.JoinManager()
        self.outputs = outputmanager.OutputManager()
        self.calc = calculator.Calculator()

        # fake threading helpers
        self.joinaborted = False
        self.executejoinqueued = False
        self.tasks_to_process = []
        self.taskinprogress = False

        # records used for showing sample output
        self.samplerecords = []

        # clear the sqlite database that's used to store all the data
        sqlitefile = open('temp.db', 'w')
        sqlitefile.truncate(0)
        sqlitefile.close()

        # init the output format combobox with the data pulled from registry
        self.gui.initoutputformatcombo(self.files.filetypes)

        # needs to be last because control goes to the gui once it's called
        gui.startgui()

    def quitprogram(self, _widget, _data=None):
        """Close open files before closing the program."""
        for datafile in self.files:
            datafile.close()
        gtk.main_quit()

    def queuetask(self, task=None):
        """Add a task to the process queue but don't start processing."""
        if task:
            self.tasks_to_process.append(task)

    def processtasks(self, task=None):
        """Process all the queued "background" tasks, like converting files."""
        if task:
            self.tasks_to_process.append(task)
        if not self.taskinprogress:
            self.taskinprogress = True
            while self.tasks_to_process:
                tasktype, taskdata = self.tasks_to_process.pop(0)
                if tasktype == 'index':
                    self.buildindex(taskdata)
                    self.updatesample()
                elif tasktype == 'sample':
                    # a needed sql table might not be created yet
                    try:
                        self.updatesample()
                    # if it fails, add it back to the end of the task list
                    except sqlite3.OperationalError:
                        self.tasks_to_process.append((tasktype, taskdata))
                elif tasktype == 'sqlite':
                    filealias, dataconverter = taskdata
                    self.converttosql(filealias, dataconverter)
        # This has to go after indexing too. The execute toggle button can be
        # used to cancel the output while the indices are still building.
            if self.executejoinqueued:
                self.gui['executejointoggle'].set_active(False)
                self.executejoin(None)
            self.taskinprogress = False

    def queueexecution(self, widget, _data=None):
        """Signal the program to start once background processing is done."""
        self.executejoinqueued = widget.get_active()
        self.processtasks()

    def buildindex(self, join):
        """Build index in the background"""
        indexalias = join.joinalias
        indexfield = join.joinfield
        self.files[indexalias].buildindex(indexfield)

    def converttosql(self, filealias, dataconverter):
        """Convert a file to an SQLite table."""
        progresstext = 'Converting to sqlite: ' + filealias
        self.gui.setprogress(0, progresstext)
        # Run the generator until it's finished. It yields % progress.
        try:
            for progress in dataconverter:
                # this progress update lets the GUI function
                self.gui.setprogress(progress, progresstext, lockgui=False)
        except ValueError:
            print 'File removed, aborting conversion.'
        self.gui.setprogress(0, '')

    def setoutputfile(self, _widget, _data=None):
        """Converts any configured output to the new output format."""
        outputfilename = self.gui['outputfilenameentry'].get_text()
        if self.gui['outputtablenameentry'].get_sensitive():
            outputtablename = self.gui['outputtablenameentry'].get_text()
        else:
            outputtablename = None
        outputfiletype = self.gui['outputtypecombo'].get_active_text()
        try:
            outputfile = self.files.openoutputfile(outputfilename,
                                                   outputfiletype,
                                                   outputtablename)
            # if NeedTableError isn't raised, disable the table entry
            # it may already be disabled, but there's no harm in being sure.
            self.gui['outputtablelabel'].set_sensitive(False)
            self.gui['outputtablenameentry'].set_sensitive(False)
        except table.NeedTableError:
            self.gui['outputtablelabel'].set_sensitive(True)
            self.gui['outputtablenameentry'].set_sensitive(True)
            # set a default table name
            outputtablename = self.joins.gettarget()
            self.gui['outputtablenameentry'].set_text(outputtablename)
            outputfile = self.files.openoutputfile(outputfilename,
                                                   outputfiletype,
                                                   outputtablename)
        # do something more here? will it ever be None?
        if outputfile is None:
            return
        self.outputs.setoutputfile(outputfile)

        fieldattributes = outputfile.getattributenames()
        self.gui.replacecolumns('outputlist', 'outputview', fieldattributes)
        outputlist = self.gui['outputlist']
        # Field calculator window setup
        self.gui['calcoutputfieldcombo'].set_model(outputlist)

        for outputfield in self.outputs:
            outputlist.append(outputfield.getattributes())
            # initialize a blank value for this field in the calculator
            blankvalue = outputfile.getblankvalue(outputfield)
            self.calc.setblankvalue(outputfield, blankvalue)

    def abortjoin(self, _widget, _data=None):
        """Set a signal for the output to abort."""
        self.joinaborted = True

    # 'execute join' button
    def executejoin(self, _widget, _data=None):
        """Execute the join and output the result"""
        if len(self.outputs) == 0:
            return

        # call this to set the filename for the output
        self.setoutputfile(None)
        outputfile = self.outputs.outputfile

        # create fields
        outputfields = [self.outputs[fn] for fn in self.outputs.outputorder]
        outputfile.setfields(outputfields)

        self.calc.clear()
        for field in self.outputs:
            self.calc.createoutputfunc(field)

        stopbutton = self.gui['stopjoinbutton']
        stopbutton.set_sensitive(True)
        self.joinaborted = False

        # sqlite setup
        joinquery = self.joins.getquery()
        print joinquery
        # open the database
        conn = sqlite3.connect('temp.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # create the table
        cur.execute(joinquery)

        # loop through target file
        i = 0
        recordcount = self.joins.getrecordcount()
        print 'total records:', recordcount
        starttime = time.time()
        while i < recordcount:
            # calculate and update the progress
            progress = float(i + 1) / recordcount
            timeelapsed = time.time() - starttime
            timetotal = timeelapsed / progress
            timeremaining = timetotal - timeelapsed
            timeend = time.localtime(starttime + timetotal)
            progresstext = ' '.join(['%f%%' % (progress * 100), '-',
                                     'Time Elapsed/Remaining/Total/ETA - ',
                                     self.timetostring(timeelapsed), '/',
                                     self.timetostring(timeremaining), '/',
                                     self.timetostring(timetotal),  '/',
                                     time.strftime('%I:%M %p', timeend)])
            print progresstext
            self.gui.setprogress(progress, progresstext)

            if self.joinaborted:
                self.gui.setprogress(0, 'Output aborted')
                stopbutton.set_sensitive(False)
                outputfile.close()
                return

            # process however many records before updating progress
            for i in range(i, min(i + 1000, recordcount)):
                # inputvalues[filealias_fieldname] = value
                inputvalues = cur.fetchone()
                newrec = {}
                outputvalues = self.calc.calculateoutput(inputvalues)
                for fieldname, fieldvalue in outputvalues:
                    newrec[fieldname] = fieldvalue

                outputfile.addrecord(newrec)

                i = i + 1

        outputfile.close()
        print 'processing complete'
        self.gui.setprogress(1, 'Output complete')

    def updatesample(self, samplesize=10):
        """Update the sample of output records"""
        if len(self.outputs) == 0:
            return

        sampleoutputfields = self.outputs.outputorder
        self.gui.replacecolumns('sampleoutputlist', 'sampleoutputview',
                                sampleoutputfields)

        self.calc.clear()
        for fieldname in sampleoutputfields:
            self.calc.createoutputfunc(self.outputs[fieldname])

        # generate a selection of records to use
        if len(self.samplerecords) != samplesize:
            self.samplerecords = []
            recordcount = self.joins.getrecordcount()
            samplesize = min(samplesize, recordcount)
            sampleindices = []
            while len(sampleindices) < samplesize:
                newindex = random.randint(0, recordcount)
                if newindex not in sampleindices:
                    sampleindices.append(newindex)

            # sqlite setup
            joinquery = self.joins.getquery(sampleindices)
            print joinquery

            # open the database
            with sqlite3.connect('temp.db') as conn:
#            conn = sqlite3.connect('temp.db')
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                # create the table
                cur.execute(joinquery)
                self.samplerecords = cur.fetchall()

        for inputvalues in self.samplerecords:
            outputrecord = []
            outputvalues = self.calc.calculateoutput(inputvalues)
            for _fieldname, fieldvalue in outputvalues:
                outputrecord.append(fieldvalue)
            self.gui['sampleoutputlist'].append(outputrecord)

    @classmethod
    def timetostring(cls, inputtime):
        """Convert a number of seconds into a human readable duration."""
        outputstr = ''
        inputtime = int(inputtime)
        seconds = inputtime % 60
        if inputtime > seconds:
            inputtime /= 60
            minutes = inputtime % 60
            if inputtime > minutes:
                inputtime /= 60
                hours = inputtime % 24
                if inputtime > hours:
                    days = inputtime / 24
                    outputstr += str(days) + 'd'
                outputstr += str(hours) + 'h'
            outputstr += str(minutes) + 'm'
        outputstr += str(seconds) + 's'
        return outputstr

DBFUTIL = DBFUtil()
