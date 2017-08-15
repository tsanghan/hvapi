# The MIT License
#
# Copyright (c) 2017 Eugene Chekanskiy, echekanskiy@gmail.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import clr
from System.Reflection import Assembly

Assembly.LoadWithPartialName("Microsoft.HyperV.PowerShell.Objects")
Assembly.LoadWithPartialName("Microsoft.HyperV.PowerShell.Cmdlets")
clr.AddReference("System.Management")

from System.Management import ManagementScope, ObjectQuery, ManagementObjectSearcher, ManagementObject, CimType, ManagementException, ManagementClass
from System import Array, String, Guid
from System.Management.Automation import PowerShell, PSObject
# WARNING, clr_Array accepts iterable, e.g. if you will pass string - it will be array of its chars, not array of one
# string. clr_Array[clr_String](["hello"]) equals to array with one "hello" string in it
clr_Array = Array
clr_String = String
# make ide happy
ManagementScope = ManagementScope
ObjectQuery = ObjectQuery
ManagementObjectSearcher = ManagementObjectSearcher
ManagementObject = ManagementObject
CimType = CimType
ManagementException = ManagementException
ManagementClass = ManagementClass
Array = Array
String = String
Guid = Guid
PowerShell = PowerShell
PSObject = PSObject
