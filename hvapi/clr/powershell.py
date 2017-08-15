from hvapi.clr.imports import PowerShell, PSObject
from hvapi.common import opencls
import functools


@opencls(PSObject)
class PSObject(object):
  @property
  def properties_dict(self):
    result = {}
    for _property in self.Properties:
      result[_property.Name] = _property.Value
    return result


# TODO utilize same powershell object
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
  def __call__(self, cmdlet, *args, **kwargs):
    ps = PowerShell.Create().AddCommand(cmdlet)
    for arg in args:
      ps.AddParameter(arg)
    for parameter_name, parameter_value in kwargs.items():
      ps.AddParameter(parameter_name, parameter_value)
    return list(ps.Invoke())

  def __getitem__(self, return_type):
    return functools.partial(self.typed_call, return_type)

  @staticmethod
  def typed_call(return_type, cmdlet, *args, **kwargs):
    ps = PowerShell.Create().AddCommand(cmdlet)
    for arg in args:
      ps.AddParameter(arg)
    for parameter_name, parameter_value in kwargs.items():
      ps.AddParameter(parameter_name, parameter_value)
    return list(ps.Invoke[return_type]())

execute_cmdlet = ExecuteCmdlet()

