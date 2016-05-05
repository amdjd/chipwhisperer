#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2016, NewAE Technology Inc
# All rights reserved.
#
#
# Find this and more at newae.com - this file is part of the chipwhisperer
# project, http://www.assembla.com/spaces/chipwhisperer
#
#    This file is part of chipwhisperer.
#
#    chipwhisperer is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    chipwhisperer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with chipwhisperer.  If not, see <http://www.gnu.org/licenses/>.
#=================================================

from datetime import *
from PySide.QtCore import *

from chipwhisperer.common.utils.parameters import Parameterized, CWParameterTree
from chipwhisperer.analyzer.utils.scripteditor import MainScriptEditor
from functools import partial


class AttackScriptGen(Parameterized):
    _name = "Attack Script Generator"

    def __init__(self, parentParam, cwGUI):
        Parameterized.__init__(self, parentParam)
        self.cwGUI = cwGUI

        self.preprocessingParamTree = CWParameterTree("Preprocessing")
        self.attackParamTree = CWParameterTree("Attack", )
        self.postprocessingParamTree = CWParameterTree("Postprocessing")

        self.utilList = []
        self.scriptList = []
        self.scriptList.append({'widget':MainScriptEditor(self.cwGUI)})
        self.scriptList[0]['filename'] = self.scriptList[0]['widget'].filename
        self.scriptList[0]['dockname'] = 'Auto-Generated'
        self.defaultEditor = self.scriptList[0]
        autogen = (self.defaultEditor['dockname'], self.defaultEditor['filename'])
        self.preprocessingListGUI = [None, None, None, None]
        self.setAttack(self.cwGUI.api.valid_attacks.get("CPA", None))

        self.params.addChildren([
            {'name':'Attack Script', 'type':'group', 'children':[
                {'name':'Filename', 'key':'attackfilelist', 'type':'filelist', 'values':{autogen:0}, 'value':0, 'editor':self.editorControl,},
                                                                 ]},
            {'name':'Pre-Processing', 'type':'group', 'children':[
                {'name':'Module #%d' % step, 'type':'list', 'values':self.cwGUI.api.valid_preprocessingModules, 'value':self.preprocessingListGUI[step], 'set':partial(self.setPreprocessing, step)} for step in range(0, len(self.preprocessingListGUI))
                                                                  ]},
            {'name':'Attack', 'type':'group', 'children':[
                {'name':'Module', 'type':'list', 'values':self.cwGUI.api.valid_attacks, 'value':self.attack, 'set':self.setAttack},
                                                          ]},
            {'name':'Post-Processing', 'type':'group'}
                                                                 ])
        self.scriptParamTree = CWParameterTree("Script", [self])
        self.cwGUI.api.sigTracesChanged.connect(self.updateAttackTraceLimits)

    def updateAttackTraceLimits(self):
        self.attack.setTraceLimits(self.cwGUI.api.project().traceManager().numTraces(), self.cwGUI.api.project().traceManager().numPoints())

    def editorControl(self, filename, filedesc, default=False, bringToFront=True):
        """This is the call-back from the script editor file list, which opens editors"""

        # Find filename
        thisEditor = None
        for e in self.scriptList:
            if e['filename'] == filename:
                thisEditor = e
                break

        if thisEditor is None:
            thisEditor = {'widget':MainScriptEditor(parent=self.cwGUI, filename=filename)}
            thisEditor['filename'] = filename
            thisEditor['dockname'] = filedesc
            self.scriptList.append(thisEditor)

        # Update all docks if required
        thisEditor['dockname'] = filedesc
        self.editorDocks()

        if bringToFront:
            thisEditor['dock'].show()
            thisEditor['dock'].raise_()

        if default:
            # Set as default for attacks etc
            self.defaultEditor = thisEditor

    def editorDocks(self):
        """Ensure we have a script editor window for each referenced analyzer script file"""

        for script in self.scriptList:
            dockname = "Analysis Script: %s" % script['dockname']

            # No previous dock, do setup
            if 'dock' not in script.keys():
                script['widget'].editWindow.runFunction.connect(partial(self.runScriptFunction, filename=script['filename']))
                script['dock'] = self.cwGUI.addDock(script['widget'], name=dockname, area=Qt.BottomDockWidgetArea)

            script['dock'].setWindowTitle(dockname)

    def setPreprocessing(self, num, module):
        """Insert the preprocessing module selected from the GUI into the list of active modules.

        This ensures that the options for that module are then displayed in the GUI, along with
        writing the auto-generated script.
        """
        if module:
            self.preprocessingListGUI[num] = module()
            self.preprocessingListGUI[num].scriptsUpdated.connect(self.reloadScripts)
        else:
            self.preprocessingListGUI[num] = None

        self.preprocessingParamTree.replace(self.preprocessingListGUI)
        self.reloadScripts()

    def setAttack(self, module):
        self.attack = module
        if module:
            self.attackParamTree.replace([self.attack])
            self.updateAttackTraceLimits()
            self.reloadScripts()
            self.attack.scriptsUpdated.connect(self.reloadScripts)
            self.attack.runScriptFunction.connect(self.runScriptFunction)

    def runScriptFunction(self, funcName, filename=None):
        """Loads a given script and runs a specific function within it."""
        mod = self.setupScriptModule(filename)
        self.cwGUI.api.runScriptModule(mod, funcName)

    def setupScriptModule(self, filename=None):
        """Loads a given script as a module for dynamic run-time insertion.

        Args:
            filename (str): The full filename to open. If None it opens the
                            auto-generated script instead.
        """

        if filename and filename != self.defaultEditor['filename']:
            raise Warning("Script Error: Cannot run script from non-default function")

        return self.defaultEditor['widget'].loadModule()

    def reloadScripts(self):
        """Rewrite the auto-generated analyzer script, using settings from the GUI"""

        # Auto-Generated is always first
        mse = self.scriptList[0]['widget']

        mse.saveSliderPosition()
        mse.editWindow.clear()

        mse.append("# Date Auto-Generated: %s" % datetime.now().strftime('%Y.%m.%d-%H.%M.%S'), 0)
        mse.append("from chipwhisperer.common.scripts._base import UserScriptBase", 0)

        # Get imports from preprocessing
        mse.append("# Imports from Preprocessing", 0)
        mse.append("import chipwhisperer.analyzer.preprocessing as preprocessing", 0)
        for p in self.preprocessingListGUI:
            if p:
                imports = p.getImportStatements()
                for i in imports: mse.append(i, 0)

        # Get imports from attack
        mse.append("# Imports from Attack", 0)
        if self.attack:
            for i in self.attack.getImportStatements():
                mse.append(i, 0)

        # Some other imports
        mse.append("# Imports from utilList", 0)
        for index, util in enumerate(self.utilList):
            if hasattr(util, '_smartstatements') and util.isVisible():
                for i in util.getImportStatements(): mse.append(i, 0)

        mse.append("", 0)

        # Add main class
        mse.append("class UserScript(UserScriptBase):", 0)
        mse.append("name = \"Auto-generated\"",1)
        mse.append("description = \"Auto-generated Attack Script\"",1)

        mse.append("def __init__(self, api):", 1)
        mse.append("UserScriptBase.__init__(self, api)")
        mse.append("self.initProject()")
        mse.append("self.initPreprocessing()")
        mse.append("self.initAnalysis()")
        mse.append("self.initReporting()")

        mse.append("def initProject(self):", 1)
        mse.append("pass")

        mse.append("def initPreprocessing(self):", 1)

        # Get init from preprocessing
        lastOutput = "self.api.project().traceManager()"
        for i, p in enumerate(self.preprocessingListGUI):
            if p and p.getName() != "None":
                classname = type(p).__name__
                instname = "ppMod%d" % i
                mse.append("%s = preprocessing.%s.%s(None, %s)" % (instname, classname, classname, lastOutput))
                for s in p.getStatements('init'):
                    mse.append(s.replace("self.", instname + ".").replace("UserScript.", "self."))
                mse.append("%s.init()" % (instname))
                lastOutput = instname
        mse.append("self.traces = %s" % lastOutput)

        # Get init from analysis
        mse.append("def initAnalysis(self):", 1)
        if self.attack:
            mse.append('self.attack = %s()' % type(self.attack).__name__)
            for s in self.attack.getStatements('init'):
                mse.append(s.replace("self.", "self.attack.").replace("UserScript.", "self."))
        else:
            mse.append('pass')

        # Get init from reporting
        mse.append("def initReporting(self):", 1)
        mse.append("# Configures the attack observers (usually a set of GUI widgets)")
        if len(self.cwGUI.api.resultWidgets)>0:
            for k, v in self.cwGUI.api.resultWidgets.iteritems():
                if hasattr(v,"setTraceSource"):
                    mse.append("self.api.resultWidgets[\"%s\"].setTraceSource(self.traces)" % k)
                if hasattr(v,"setAnalysisSource"):
                    mse.append("self.api.resultWidgets[\"%s\"].setAnalysisSource(self.attack)" % k)
        else:
            mse.append("pass")

        # Do the attack
        mse.append("def run(self):", 1)
        mse.append("self.attack.processTraces()")

        # Get other commands from attack module
        if self.attack:
            for k in self.attack._smartstatements:
                if k == 'init' or k == 'go' or k == 'done':
                    pass
                else:
                    mse.append("def %s(self):" % k, 1)
                    for s in self.attack.getStatements(k):
                        mse.append(s.replace("self.", "self.api.getAttack().").replace("UserScript.", "self."))

        # Get other commands from other utilities
        for index, util in enumerate(self.utilList):
            if hasattr(util, '_smartstatements') and util.isVisible():
                for k in util._smartstatements:
                    util._smartstatements[k].addSelfReplacement("utilList[%d]." % index)
                    util._smartstatements[k].addSelfReplacement("parent.")
                    statements = util.getStatements(k)

                    if len(statements) > 0:
                        mse.append("def %s_%s(self):" % (util.__class__.__name__, k), 1)
                        for s in statements:
                            mse.append(s.replace("UserScript.", "self."))

        mse.restoreSliderPosition()
        self.cwGUI.api.runScriptModule(self.setupScriptModule(), None)