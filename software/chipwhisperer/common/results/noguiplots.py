#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2018, NewAE Technology Inc
# All rights reserved.
#
#
# Find this and more at newae.com - this file is part of the chipwhisperer
# project, https://github.com/newaetech/chipwhisperer
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

from chipwhisperer.common.utils.util import DictType
import numpy as np

class NoGUIPlots(object):
    def __init__(self, attack_results=None):
        self._results = attack_results
        
    def setResults(self, attack_results):
        self._results = attack_results
        
    def corrVsTrace(self, bnum):
        attack_results = self._results
        data = attack_results.maxes_list
        maxdata = data[bnum]
        tlist = []
        for m in maxdata:
            tlist.append(m['trace'])
        maxlist = np.zeros((len(attack_results.diffs[bnum]), len(tlist)))
        for i, m in enumerate(maxdata):
            for j in range(0, len(attack_results.diffs[bnum])):
                maxlist[m['maxes'][j][0], i] = m['maxes'][j][2]
                
        return [tlist, maxlist]
                
    def pgeVsTrace(self, bnum):
        attack_results = self._results
        pge = attack_results.pge_total
        allpge = DictType()

        for i in pge:
            tnum = i['trace']
            if not tnum in allpge:
                allpge[tnum] = [{'pgesum':0, 'trials':0} for z in range(0,attack_results.numSubkeys)]

            allpge[tnum][i['subkey']]['pgesum'] += i['pge']
            allpge[tnum][i['subkey']]['trials'] += 1

        for (tnum, plist) in allpge.items():
            for j in plist:
                if j['trials'] > 0:
                    j['pge'] = float(j['pgesum']) / float(j['trials'])
                    # print "%d "%j['trials'],
                else:
                    j['pge'] = None

        trace = []
        pge = []
        for (tnum, plist) in allpge.items():
            if plist[bnum]['pge'] is not None:
                trace.append(tnum)
                pge.append(plist[bnum]['pge'])

        return [trace, pge]
    
    def outputVsTime(self, bnum):
        if self._results is None:
            return None
        
        attack_results = self._results
        
        ## get < key data
        key = attack_results.knownkey[bnum]
        data = attack_results.diffs[bnum]
        
        xrangelist = range(0, len(data[0]))

        max1 = np.amax(data[0:key-1], 0)
        min1 = np.amin(data[0:key-1], 0)

        arr1 = np.zeros(len(data[0]))
        for obj in enumerate(max1):
            i = obj[0]
            if abs(max1[i]) > abs(min1[i]):
                arr1[i] = max1[i]
            else:
                arr1[i] = min1[i]

        ## get > key data
        max2 = np.amax(data[key+1:-1], 0)
        min2 = np.amin(data[key+1:-1], 0)

        arr2 = np.zeros(len(data[0]))
        for obj in enumerate(max1):
            i = obj[0]
            if abs(max2[i]) > abs(min2[i]):
                arr2[i] = max2[i]
            else:
                arr2[i] = min2[i]

        return [xrangelist, data[key], arr1, arr2]