from hvapi.clr.imports import PowerShell, PSObject
from hvapi.common import opencls
import functools
import threading


@opencls(PSObject)
class PSObject(object):
  @property
  def properties(self):
    result = {}
    for _property in self.Properties:
      result[_property.Name] = _property.Value
    return result


class ExecuteCmdlet(object):
  """
  Class for executing pwershell based cmdlets.
  Supports typed invocation, e.g particular c# type will be returned instead of PSObject.

  Example of typed invocation::

    from Microsoft.Vhd.PowerShell import VirtualHardDisk

    @opencls(VirtualHardDisk)
    class VirtualHardDisk(object):
        @property
        def hello(self):
          return "Hello, World"

    result = ExecuteCmdlet()[VirtualHardDisk]("Get-VHD", Path=r"disk.vhdx")[-1]
    # result is a list of Microsoft.Vhd.PowerShell.VirtualHardDisk instances
    print(result.hello) # prints 'Hello, World' because VirtualHardDisk was reopened and 'hello' property was added


  Typed invocation is useful for returning opened c# types with custom properties.
  """

  def __init__(self):
    self._powershell = threading.local()

  @property
  def powershell(self) -> PowerShell:
    ps = getattr(self._powershell, 'ps', None)
    if ps is None:
      ps = PowerShell.Create()
      self._powershell.ps = ps
    return ps

  def __call__(self, cmdlet, *args, **kwargs):
    return self.typed_call(PSObject, cmdlet, *args, **kwargs)

  def __getitem__(self, return_type):
    return functools.partial(self.typed_call, return_type)

  def typed_call(self, return_type, cmdlet, *args, **kwargs):
    try:
      ps = self.powershell.AddCommand(cmdlet)
      for arg in args:
        ps.AddParameter(arg)
      for parameter_name, parameter_value in kwargs.items():
        ps.AddParameter(parameter_name, parameter_value)
      result = ps.Invoke[return_type]()
      if ps.Streams.Error.Count > 0:
        error_record = ps.Streams.Error[ps.Streams.Error.Count-1]
        exception = error_record.Exception
        raise exception
      return list(result)
    finally:
      ps.Streams.Error.Clear()
      ps.Commands.Clear()


execute_cmdlet = ExecuteCmdlet()
