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
from typing import Union

from hvapi.clr.powershell import execute_cmdlet
from hvapi.common import opencls
from hvapi.disk.types import VHDType, VHDFormat

from Microsoft.Vhd.PowerShell import VirtualHardDisk as _VirtualHardDisk


class VHDDisk(object):
  def __init__(self, disk_path=None, vhd=None):
    if not disk_path:
      if not vhd:
        raise Exception("VHD object or VHD path must be specified")
      else:
        self.vhd = vhd
    else:
      self.vhd = execute_cmdlet[_VirtualHardDisk]("Get-VHD", Path=disk_path)[-1]

  @property
  def Alignment(self) -> int:
    return self.vhd.Alignment

  @property
  def Attached(self) -> bool:
    return self.vhd.Attached

  @property
  def BlockSize(self) -> int:
    return self.vhd.BlockSize

  @property
  def ComputerName(self) -> str:
    return self.vhd.ComputerName

  @property
  def DiskIdentifier(self) -> str:
    return self.vhd.DiskIdentifier

  @property
  def DiskNumber(self) -> Union[int, type(None)]:
    return self.vhd.DiskNumber

  @property
  def FileSize(self) -> int:
    return self.vhd.FileSize

  @property
  def FragmentationPercentage(self) -> Union[int, type(None)]:
    return self.vhd.FragmentationPercentage

  @property
  def LogicalSectorSize(self) -> int:
    return self.vhd.LogicalSectorSize

  @property
  def MinimumSize(self) -> Union[int, type(None)]:
    return self.vhd.MinimumSize

  @property
  def ParentPath(self) -> str:
    return self.vhd.ParentPath

  @property
  def Path(self) -> str:
    return self.vhd.Path

  @property
  def PhysicalSectorSize(self) -> int:
    return self.vhd.PhysicalSectorSize

  @property
  def Size(self) -> int:
    return self.vhd.Size

  @property
  def VhdFormat(self) -> VHDFormat:
    return VHDFormat(self.vhd.VhdFormat)

  @property
  def VhdType(self) -> VHDType:
    return VHDType(self.vhd.VhdType)

  def clone(self, clone_path, differencing=True):
    """
    Creates clone of current vhd disk.

    :param clone_path: path where cloned disk will be stored
    :param differencing: indicates if disk must be thin-copy
    :return: resulting VHDDisk
    """
    if differencing:
      # New-VHD –ParentPath "C:\Users\evhenii\Desktop\centos7\centos7\Virtual Hard Disks\centos7.vhdx" –Path c:\Diff.vhdx - Differencing
      return VHDDisk(vhd=execute_cmdlet[_VirtualHardDisk]("New-VHD", ParentPath=self.Path, Path=clone_path)[-1])
    else:
      execute_cmdlet("Copy-Item", Path=self.Path, Destination=clone_path)
      return VHDDisk(disk_path=clone_path)
