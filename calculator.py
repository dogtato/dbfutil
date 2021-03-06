"""Converts input records to output records.

This class serves two purposes:
* Calculates the output values for each field
** Call createoutputfunc(field) for each output field
** Call calculateoutput(inputvalues) to get all output values
* Creates and edits custom functions that can be used for calculating output
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
import re
import os
import sys
import traceback
from collections import OrderedDict

# libraries to preload and list in the calculator dialog
# XXX needs a menu setting to edit it. in place or make a config file?
DEFAULT_LIBRARIES = ['default', 'temporary', 'math']


class Calculator(object):
    """This class creates custom functions for each of the output fields."""
    def __init__(self):
        self.outputfuncs = OrderedDict()
        self.inputblanks = {}
        self.moremodules = {}
        # list of all the modules the user can edit
        self.custommodules = []
        # stores text of libraries to detect changes
        # this allows an external editor to be used to make changes
        self.libtext = {}

        # reset the file for storing temporary functions. resetting when the
        # program starts means the functions will remain available in case
        # they're wanted after all.
        os.chdir('fieldcalcs')
        templib = open('temporary.py', 'w')
        templib.truncate(0)
        templib.close()
        os.chdir('..')

        # load all the libraries set to load by default
        for libname in DEFAULT_LIBRARIES:
            self._importlib(libname)
        self.moremodules['builtins'] = __builtins__

        # import everything from the fieldcalcs directory
        customfuncs = os.listdir('fieldcalcs')
        for funcname in customfuncs:
            if funcname.endswith('.py'):
                name = funcname.split('.')[0]
                if self._importlib(name):
                    self.libtext[name] = self._getlibtext(name)
                    self.custommodules.append(name)

    def clear(self):
        """Clear the list of dynamically generated output functions."""
        self.outputfuncs = OrderedDict()

    def _importlib(self, libname):
        """Import a library for the calculator to use."""
        libname = libname.strip()
        if libname is '':
            return
        if libname not in self.moremodules:
            try:
                # try this way in case it's a python library module
                self.moremodules[libname] = __import__(libname)
            except ImportError:
                # check if it's a file in fieldcalcs
                if self._getlibtext(libname) is not None:
                    try:
                        self.moremodules[libname] = __import__('fieldcalcs.' +
                                                               libname,
                                                               globals(),
                                                               locals(),
                                                               [libname])
                    except:
                        print "Exception in user code:"
                        print '-'*60
                        traceback.print_exc(file=sys.stdout)
                        print '-'*60
                        return False
                else:
                    return False
        return True

    def createlib(self, libname):
        """Create a new library file in the fieldcalcs directory."""
        if libname not in self.moremodules:
            os.chdir('fieldcalcs')
            newlib = open(libname + '.py', 'w')
            newlib.close()
            os.chdir('..')
            if self._importlib(libname):
                self.custommodules.append(libname)

    def getlibs(self):
        """Get a list of all libraries currently imported for field calcs."""
        return self.moremodules

    def getcustomlibs(self):
        """Get a list of all the custom libraries."""
        return self.custommodules

    def getfuncs(self, libname):
        """Get the names of all public functions in a library."""
        if libname is '':
            return
        if libname not in self.moremodules:
            if self._importlib(libname) == False:
                return []
        # check if file has been updated and reload it
        self._getlibtext(libname)
        libfuncs = []
        # get a list of all the names defined in the function
        names = dir(self.moremodules[libname])
        for name in names:
            libobject = getattr(self.moremodules[libname], name)
            # filter out other modules that were imported
            if callable(libobject):
                # filter out private methods:
                if not name.startswith('_'):
                    # return a tuple of the function name and docstring
                    libfuncs.append((name, libobject.__doc__))
        return libfuncs

    # this is only used for custom functions defined in a fieldcalcs module
    def getfunctext(self, libname, funcname):
        """Parse a library file and get the full text of a given function."""
        libtext = self._getlibtext(libname)
        funcstart, funcend = self._getfuncbounds(libtext, funcname)
        # return the function as a single string
        return ''.join(libtext[funcstart:funcend + 1])

    # this is only used for custom functions defined in a fieldcalcs module
    @classmethod
    def _getfuncbounds(cls, libtext, funcname):
        """Parse a library file and get the start/end of a given function."""
        i = 0
        funcstart = -1
        funcend = -1
        # find the start of the function
        startpattern = re.compile('def ' + funcname)
        while i < len(libtext):
            if startpattern.match(libtext[i]):
                funcstart = i
                # backtrack and grab comments that precede the function
                while libtext[funcstart - 1].strip().startswith('#'):
                    funcstart -= 1
                break
            i += 1
        else:
            # function not found
            return (None, None)
        # move to the first indented line
        i += 1
        # find the end of the function (an unindented, uncommented line)
        endpattern = re.compile(r'[ #]{4}')
        while i < len(libtext):
            if endpattern.match(libtext[i]):
                funcend = i
                i += 1
            else:
                break

        # return the function as a single string
        return (funcstart, funcend)

    # this is only used for custom functions defined in a fieldcalcs module
    def _getlibtext(self, libname):
        """Returns the text of a python library file as a list of lines."""
        os.chdir('fieldcalcs')
        try:
            libfile = open(libname + '.py', 'r')
        except IOError:
            # not a fieldcalcs module
            os.chdir('..')
            return None
        os.chdir('..')
        libtext = libfile.readlines()
        libfile.close()
        if libname not in self.libtext:
            self.libtext[libname] = libtext
        elif self.libtext[libname] != libtext:
            # reload the module so the new function can be used
            # this could cause interesting sequences of events when called
            # from writefunctext, hopefully only if the user does unusual
            # things like adding a broken function then saving
            try:
                self.moremodules[libname] = reload(self.moremodules[libname])
                self.libtext[libname] = libtext
            except:
                print "Exception in user code:"
                print '-'*60
                traceback.print_exc(file=sys.stdout)
                print '-'*60
                return None
        return libtext

    def codeisvalid(self, codeblock):
        testenv = {}
        try:
            exec ''.join(codeblock) in testenv
        except:
            # XXX pop up an alert instead?
            print "Exception in user code:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60
            return False
        return True

    def writefunctext(self, libname, text):
        """Save a function written in the gui to a file."""
        curtext = self._getlibtext(libname)
        if curtext is None:
            print 'Error in library, function not saved.'
            return
        # replace any tabs with four spaces
        spacedtext = re.sub(r'\t', '    ', text)
        # this formats the input string like readlines() does for files
        newtext = [line + '\n' for line in spacedtext.split('\n')]
#        re.findall(r'.*\n*', spacedtext)
        # extract the function names from the function text.
        funcnames = re.findall(r'def ([a-zA-Z_][a-zA-Z_0-9]*)\(', text)
        for funcname in funcnames:
            curfuncstart, curfuncend = self._getfuncbounds(curtext, funcname)
            newfuncstart, newfuncend = self._getfuncbounds(newtext, funcname)
            if self.codeisvalid(newtext[newfuncstart:newfuncend + 1]):
                # if the function is already in the file, replace it
                if curfuncstart:
                    # Add portion of the library before the function being replaced
                    outputtext = curtext[:curfuncstart]
                    # Add the new function to lines
                    outputtext.extend(newtext[newfuncstart:newfuncend + 1])
                    # Add portion of the library after the function being replaced
                    outputtext.extend(curtext[curfuncend + 1:])
                    curtext = outputtext
                else:
                    curtext.extend(['\n', '\n'])
                    curtext.extend(newtext[newfuncstart:newfuncend + 1])
        # if there were any functions to write, do so and reload the library
        if len(funcnames) > 0:
            os.chdir('fieldcalcs')
            libfile = open(libname + '.py', 'w')
            libfile.truncate(0)
            libfile.write(''.join(curtext))
            libfile.close()
            os.chdir('..')
            # reload the module so the new function can be used
            self.moremodules[libname] = reload(self.moremodules[libname])

    # Doesn't need to be speedy, but the function it creates does
    # Not a lot of room for optimizing, that I can imagine
    def createoutputfunc(self, field):
        """Converts an expression to a single function call.

        Converts field['value'] to a function that can be quickly executed
        during output.

        The field value can contain several types of arguments:
        * constant values: 8. 'cat', [0, 1, 2, 3]
        * input field values: !filealias.fieldname!
        * builtin function calls: len(), str(), abs()
        * library function calls: math.sqrt(), os.getcwd()
        * custom functions defined in fieldcalcs.default: pad_ids()
        * functions from a different module in fieldcalcs: streets.fullname()
        (fullname function is defined in streets.py)

        The only novel syntax is for input field values.
        The function assumes the user has written everything correctly.
        """
        newfuncname = field['name']
        newfuncbody = field['value']
        argpos = 0
        # Convert all !filealias.fieldname! to usable argument references
        args = re.findall(r'![a-zA-Z0-9_]+\.[a-zA-Z0-9_]+!', newfuncbody)
        for arg in args:
            internalname = 'args[' + str(argpos) + ']'
            argpos += 1
            newfuncbody = re.sub(arg, internalname, newfuncbody)

        # Convert all the function calls to callable references
        funcs = re.findall(r'([a-zA-Z]+[a-zA-Z0-9\._]*)\(', newfuncbody)
        for funcname in funcs:
            components = funcname.split('.')
            # A single word is either a builtin, default, or temporary function
            if len(components) == 1:
                # first check if it's a temporary function
                # this means temp functions will overrule default functions
                # defaults or builtins can still be used by writing
                # default.func or builtins.func
                if components[0] in dir(self.moremodules['temporary']):
                    # prepend 'temporary.' to the function name
                    newfuncbody = re.sub(funcname,
                                         'self.moremodules["temporary"].' +
                                         funcname, newfuncbody)
                # then check if it's in default
                elif components[0] in dir(self.moremodules['default']):
                    # prepend 'default.' to the function name
                    newfuncbody = re.sub(funcname,
                                         'self.moremodules["default"].' +
                                         funcname, newfuncbody)
                # otherwise assume it's a builtin and leave it alone
                # XXX should check builtins and do something if it isn't there
            else:
                # if it has a module name, make sure the module is imported
                module = components[0]
                self._importlib(module)
                if module in self.moremodules:
                    # replace the module name with a reference to the locally
                    # imported module
                    newmodule = 'self.moremodules["' + module + '"]'
                    newfuncbody = re.sub(module, newmodule, newfuncbody)

        # define the new function to wrap the expression
        # prepend func_ to avoid name conflicts
        newfuncstr = 'def func_' + newfuncname + '(self, args):\n'
        newfuncstr = newfuncstr + '    return ' + newfuncbody

        # create the function and return it with the list of args it needs
        tempcontext = {}
        exec(newfuncstr) in tempcontext
        for i in range(len(args)):
            # trim the leading and trailing '!'s and replace '.' with '_'
            # cast to str in case it's unicode. sqlite3.Row uses ascii keys
            # and the dictionary of input values is an sqlite3.Row
            args[i] = str(re.sub(r'\.', '_', args[i][1:-1]))
        self.outputfuncs[newfuncname] = (tempcontext['func_' + newfuncname],
                                         args)

    # needs to be speedy
    # inputvalues is an sqlite3.Row, which is like a dict but
    # doesn't support 'in'
    def calculateoutput(self, inputvalues):
        """Takes all the input records and computes the output record.

        Each of the output functions created by createoutputfunc() is called
        using inputvalues."""
        outputvalues = []
        for outputfieldname in self.outputfuncs:
            outputfunc, args = self.outputfuncs[outputfieldname]
            argvalues = []
            outputvalue = None
            for arg in args:
                # arg might not be a valid name of an input field
                try:
                    argvalue = inputvalues[arg]
                # this should only be thrown when calculating sample output
                # and the error should be spotted and fixed before full output
                except IndexError:
                    outputvalue = '##BAD ARG: ' + arg + '##'
                    break
                if argvalue is not None:
                    argvalues.append(argvalue)
                else:
                    # Missed join for this record, pass a blank default value
                    argvalues.append(self.inputblanks[arg])
            if outputvalue is None:
                try:
                    outputvalue = outputfunc(self, argvalues)
                except:
                    # This will be shown in the sample output. Should be enough
                    # feedback on when something is not working so '##ERROR##'
                    # won't get written to [m]any output files
                    print "Exception in user code:"
                    print '-'*60
                    traceback.print_exc(file=sys.stdout)
                    print '-'*60
                    outputvalue = '##ERROR##'

            outputvalues.append((outputfieldname, outputvalue))
        return outputvalues

    # doesn't need to be speedy
    def setblankvalue(self, field, value):
        """Stores a default blank value to use for each input field."""
        if field.source is not None:
            self.inputblanks[field.source + '_' + field.originalname] = value

    @classmethod
    def reloadcalcfuncs(cls):
        """Reloads the module in case a user has added a new function to it."""
        reload('calcfunctions')
