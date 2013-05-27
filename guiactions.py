# -*- coding: utf-8 -*-
# methods that respond to and update the GUI and pass the rest off as much as possible
# I'm also going to try to limit access to App's allfiles and targetfile attributes

#import Tkinter #imported via gui via filemanager
#import re #imported via gui via filemanager
import Tkinter
import re

import gui
import filemanager
import joinmanager
import outputmanager
#import joinfile #imported via gui via filemanager

class DBFUtil(object):
    def __init__(self):
        self.app = gui.initapp(self)
        self.files = filemanager.FileManager()
        self.joins = joinmanager.JoinManager()
        self.outputs = outputmanager.OutputManager()
        # needs to be last because it stays in the gui mainloop
        gui.startapp(self.app)

    # 'add dbf' button
    def openjoin(self):
        """Open a new file for joining to the target."""
        newfilealias = self.files.addfile()
        # checks that a file was selected
        if newfilealias:
            # check if file is in the lists already
            if newfilealias not in self.app.dbftargetlist.get(0, Tkinter.END):
                self.app.dbftargetlist.insert(Tkinter.END, newfilealias)
                self.app.dbfjoinlist.insert(Tkinter.END, newfilealias)
        return newfilealias
    
    # 'select target dbf' button. remove opening a new file and instead just set it to an already open file?
    def opentarget(self):
        """Open a new file or set an already open file as the target for joining."""
        newfilealias = self.openjoin()
        if newfilealias:
            # set target
            self.joins.settarget(newfilealias)
            # set the gui label for showing the full path to the target
            self.app.target.__setitem__('text',newfilealias)
    
    # 'remove dbf' button
    def removejoin(self):
        """Close a file and remove all joins that depend on it."""
        # get filename of file selected to be removed
        selected = self.app.dbftargetlist.curselection()
        if selected:
            filename =self. app.dbftargetlist.get(selected[0])
            
            # remove file
            self.files.removefile(filename)
            # remove joins that depend on the file
            self.joins.removefile(self.files[filename].alias)
            
            # remove from gui list and from the fields dictionary
            self.app.dbftargetlist.delete(selected[0])
            self.app.dbfjoinlist.delete(selected[0])
        
    # 'config selected' button
    def loadjoinchoices(self):
        """Populate the second set of listboxes with the fields from the selected files."""
        target = self.joins.gettarget()
    #   clear the lists before adding fields of selected table and join table
        self.app.target_list.delete(0,Tkinter.END)
        self.app.join_list.delete(0,Tkinter.END)
    
        targetindex = self.app.dbftargetlist.curselection()
        joinindex = self.app.dbfjoinlist.curselection()
        if targetindex and joinindex:
            targetalias = self.app.dbftargetlist.get(targetindex)
            joinalias = self.app.dbfjoinlist.get(joinindex)
        
            # verify that the selectedtarget is joined to the overall target
            if self.joins.checkjoin(target, targetalias) == False:
                print 'Join to the global target first.'
            # Check that selected target  ISN'T joined to selected join
            # this would create a problematic circular join. 
            # If it needs to be done, open the file again to get another alias and use that
            elif self.joins.checkjoin(joinalias, targetalias):
                print 'Cannot create circular join. Reopen the file to use a different alias.'
            else:
                self.joins.curtarget = targetalias
                self.joins.curjoin = joinalias
                for field in self.files[targetalias].getfields():
                    self.app.target_list.insert(Tkinter.END, field.name)
                for field in self.files[joinalias].getfields():
                    self.app.join_list.insert(Tkinter.END, field.name)
                
    # 'apply' join choice button
    def savejoinchoice(self):
        """Save join using the selected fields in the gui."""
        # get join field names
        targetindex = self.app.target_list.curselection()
        joinindex = self.app.join_list.curselection()
        if targetindex and joinindex:
            targetfield = self.app.target_list.get(targetindex[0])
            joinfield = self.app.join_list.get(joinindex[0])
        
            # save to joins
            self.joins.addjoin(targetfield, joinfield)
        
            # clear boxes to show that the join is applied
            self.app.target_list.delete(0,Tkinter.END)
            self.app.join_list.delete(0,Tkinter.END)

    # 'init output' button
    # populate the list of output fields with all the input fields
    def initoutput(self):
        """Initialize the list of output fields and add all fields to the OutputManager."""
        # delete any fields already entered
        self.outputs.clear()
        self.app.output_list.delete(0,Tkinter.END)
        
        # check that a target file has been opened
        if self.joins.targetalias:
            # add all the fields from the target and everything joined to it
            for filealias in self.joins.getjoinedaliases():
                for field in self.files[filealias].getfields():
                    newField = self.outputs.addfield(field, filealias)
                    self.app.output_list.insert(Tkinter.END, newField.outputname)

    # 'del field' button
    def removeoutput(self):
        """Remove a field from the output."""
        # get the indices of the selected fields
        selected = [int(item) for item in self.app.output_list.curselection()]
        selectednames = [self.app.output_list.get(i) for i in selected]

        ef = self.outputs.editField
        self.outputs.removefields(selectednames)
        
        # clear the fields if the field loaded for editing was just removed
        if ef and not self.outputs.editField:
            self.app.outputname.delete(0,Tkinter.END)
            self.app.outputvalue.delete(1.0,Tkinter.END)
            self.app.fieldtype.delete(0,Tkinter.END)
            self.app.fieldlen.delete(0,Tkinter.END)
            self.app.fielddec.delete(0,Tkinter.END)
        
        # reverse the list to delete from the back so the indices don't get messed up as we go
        selected.reverse()
        for index in selected:
            self.app.output_list.delete(index)

    # 'move up' button
    def moveup(self):
        """Move the selected items up in the list of output fields."""
        # get the indices of the selected fields
        selected = [int(item) for item in self.app.output_list.curselection()]
        if len(selected) > 0:
            newselection = self.outputs.movefieldsup(selected)
    
            # update gui list with new order
            self.app.output_list.delete(0,Tkinter.END)
            for field in self.outputs:
                self.app.output_list.insert(Tkinter.END, field.outputname)
            
            # keep the same entiries in the list highlighted after moving them
            self.app.output_list.selection_clear(0, Tkinter.END)
            for index in newselection:
                self.app.output_list.selection_set(index)
            self.app.output_list.see(newselection[0]-1)

    # 'move down' button
    def movedown(self):
        """Move the selected items up in the list of output fields."""
        # get the indices of the selected fields
        selected = [int(item) for item in self.app.output_list.curselection()]
        if len(selected) > 0:
            newselection = self.outputs.movefieldsdown(selected)
            
            # update gui list with new order
            self.app.output_list.delete(0,Tkinter.END)
            for field in self.outputs:
                self.app.output_list.insert(Tkinter.END, field.outputname)
                    
            # keep the same entiries in the list highlighted after moving them
            self.app.output_list.selection_clear(0, Tkinter.END)
            for index in newselection:
                self.app.output_list.selection_set(index)
            self.app.output_list.see(newselection[-1]+1)
        

    # 'config selected field' button
    def configoutput(self):
        """Load field data into the GUI for editing."""
        # save the pos of the first selected field, which will be the one loaded for editing
        selection = self.app.output_list.curselection()
        if selection:
            self.outputs.seteditfield(selection[0])
            curfield = self.outputs.editField
            
            # Clear then load the GUI field with the values
            self.app.outputname.delete(0,Tkinter.END)
            self.app.outputvalue.delete(1.0,Tkinter.END)
            self.app.fieldtype.delete(0,Tkinter.END)
            self.app.fieldlen.delete(0,Tkinter.END)
            self.app.fielddec.delete(0,Tkinter.END)
            self.app.outputname.insert(Tkinter.END, curfield.outputname)
            self.app.outputvalue.insert(Tkinter.END, curfield.value)
            self.app.fieldtype.insert(Tkinter.END, curfield.type)
            self.app.fieldlen.insert(Tkinter.END, curfield.len)
            self.app.fielddec.insert(Tkinter.END, curfield.dec)
        
    # 'save field' button
    def saveoutput(self):
        """Save the modified attributes of a field."""
        # get the new values and do basic tests for validity
        newname = self.app.outputname.get()
        if newname == '' or newname[0].isdigit():
            return
        newvalue = self.app.outputvalue.get(1.0,Tkinter.END).strip()
        newtype = self.app.fieldtype.get().upper()
        if newtype.upper() not in self.outputs.fieldtypes:
            return
        newlen = self.app.fieldlen.get()
        if newlen.isdigit():
            newlen = int(newlen)
        else:
            return
        newdec = self.app.fielddec.get()
        if newdec.isdigit():
            newdec = int(newdec)
        else:
            return
        
        # this should be resilient to loading a field, moving fields around, then saving the field
        fieldindex = self.outputs.getindex(self.outputs.editField)
        
        # save the new field attributes
        result = self.outputs.saveeditfield(newname, newvalue, newtype, newlen, newdec)
        if result != 'ok':
            print result
            return
                
        # refresh the field name in the gui then select and scroll to it
        self.app.output_list.delete(fieldindex)
        self.app.output_list.insert(fieldindex,newname)
        self.app.output_list.selection_clear(0,Tkinter.END)
        self.app.output_list.selection_set(fieldindex)
        self.app.output_list.see(fieldindex)
        # clear the gui field attribute fields
        self.app.outputname.delete(0,Tkinter.END)
        self.app.outputvalue.delete(1.0,Tkinter.END)
        self.app.fieldtype.delete(0,Tkinter.END)
        self.app.fieldlen.delete(0,Tkinter.END)
        self.app.fielddec.delete(0,Tkinter.END)
        
    # 'add field' button
    def addoutput(self):
        # get the new values and do basic tests for validity
        newname = self.app.outputname.get()
        if newname == '' or newname[0].isdigit():
            return
        newvalue = self.app.outputvalue.get(1.0,Tkinter.END).strip()
        newtype = self.app.fieldtype.get().upper()
        if newtype.upper() not in self.outputs.fieldtypes:
            return
        newlen = self.app.fieldlen.get()
        if newlen.isdigit():
            newlen = int(newlen)
        else:
            return
        newdec = self.app.fielddec.get()
        if newdec.isdigit():
            newdec = int(newdec)
        else:
            return
        
        # if a field is selected, insert the new field after it. otherwise insert it at the end
        selected = self.app.output_list.curselection()
        if len(selected) > 0:
            newindex = int(selected[0]) + 1
        else:
            newindex = 'end'
        # add the field. If newfieldname is already in use, it will generate a unique name instead
        newfieldname = self.outputs.addnewfield(newname, newvalue, newtype, newlen, newdec, newindex)
        
        # add the fiel
        self.app.output_list.insert(newindex,newfieldname)
        self.app.output_list.selection_clear(0,Tkinter.END)
        self.app.output_list.selection_set(newindex)
        self.app.output_list.see(newindex)
        # not clearing will allow adding lots of similar fields more quickly
#        app.outputname.delete(0,END)
#        app.outputvalue.delete(1.0,END)
#        app.fieldtype.delete(0,END)
#        app.fieldlen.delete(0,END)
#        app.fielddec.delete(0,END)

    # 'execute join' button
    def dojoin(self):
        """Execute the join and output the result"""
        if len(self.outputs) == 0:
            return
        # build indexes of the join fields
        self.buildindexes()
    
        targetalias = self.joins.gettarget()
        targetfile = self.files[targetalias]
        
        # create output file. I think it will cleanly overwrite the file if it already exists
        outputfilename = self.app.outputfilename.get()
        outputfile = self.files.openoutputfile(outputfilename)
        
        # create fields
        for fieldname in self.outputs.outputorder:
            outputfile.addfield(self.outputs[fieldname])
    
        # loop through target file
        i = 0
        recordcount = targetfile.getrecordcount()
        print 'total records:', recordcount
        while i < recordcount:
            print 'processing record: ', i, '%f%%'%(float(i)/recordcount*100)
            # process however many records before updating status
            for i in range(i, min(i+1000,recordcount)):
                # inputvalues[filealias][fieldname] = value
                inputvalues = {}
                inputvalues[targetalias] = targetfile[i]
                
                for joinlist in self.joins:
                    for join in joinlist:
                        joinvalue = inputvalues[join.targetalias][join.targetfield]
                        joinFile = self.files[join.joinalias]
                        # Will be None if there isn't a matching record to join
                        temprecord = joinFile.getjoinrecord(join.joinfield, joinvalue)
                        if temprecord is None:                            
                            print join.joinfield+':', joinvalue, '- not found'
                        else:
                            inputvalues[join.joinalias] = temprecord
    
#                print 'inputvalues', inputvalues
                newrec = {}
                for field in self.outputs:
                    # field.value ex: '!file0.field0! + !file1.field1!'
                    fieldrefs = re.findall('!([^!]+)!', field.value)
                    fieldvalue = str(field.value)
                    # Replace eacy file.field reference with the actual value
                    for fieldref in fieldrefs:
                        filealias, fieldname = fieldref.split('.')
#                        print refsplit
                        # check that each referenced file was successfully joined
                        if filealias in inputvalues:
                            refvalue = inputvalues[filealias][fieldname]
                            fieldvalue = re.sub('!'+fieldref+'!', str(refvalue), fieldvalue)
                        # if it didn't join, use a blank value
                        else:
                            # insert a blank value for the reference that matches the type of the output field
                            # with more effort, it could match the type of the field that didn't get joined
                            fieldvalue = re.sub('!'+fieldref+'!', str(self.blankvalue(field)), fieldvalue)
                        
                    # Apply any calculating. Want to make compatible with the arcmap field calculator.
                    # That is extra functionality, with a second input field for the code block
                    try:
                        newrec[field.outputname] = eval(fieldvalue)
                    except NameError:
                        newrec[field.outputname] = fieldvalue
                    except SyntaxError:
                        newrec[field.outputname] = fieldvalue
                    except TypeError:
                        newrec[field.outputname] = fieldvalue
                
                outputfile.addrecord(newrec)
                                
                i = i + 1
                
        outputfile.close()
        print 'processing complete'
#        for joinfile in self.files:
#            print joinfile
#            joinfile.close()
        
    # util function used in dojoin()
    # building an index for each join dbf file is better than trying to sort the files
    # an index is needed so that, as it goes through the target table, record by record,
    # we can quickly find the correct record with the index and jump straight to it
    def buildindexes(self):
        for filealias in self.joins.getjoinedaliases():
            if filealias in self.joins:
                for join in self.joins[filealias]:
                    self.files[join.joinalias].buildindex(join.joinfield)

    # util function used in dojoin()
    # this is all arbitrary
    def blankvalue(self, field):
        if field.type == 'N':
            return 0
        elif field.type == 'F':
            return 0.0
        elif field.type == 'C':
            return ''
        # i don't know for this one what a good nonvalue would be
        elif field.type == 'D':
            return (0,0,0)
        elif field.type == 'I':
            return 0
        elif field.type == 'Y':
            return 0.0
        elif field.type == 'L':
            return -1
        elif field.type == 'M':
            return " " * 10
        elif field.type == 'T':
            return

dbfUtil = DBFUtil()



