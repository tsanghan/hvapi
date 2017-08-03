import clr
clr.AddReference("System.Management")
from System.Management import ManagementScope, ObjectQuery, ManagementObjectSearcher, ManagementObject, CimType, ManagementException, ManagementClass
from System import Array, String, Guid
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
