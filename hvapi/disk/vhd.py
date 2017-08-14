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
from hvapi.disk.internal import open_vhd, get_vhd_info, GUID, create_vhd, close_handle
from hvapi.disk.types import ProviderSubtype, VirtualStorageType, VHDException


def transform_property(member_name, value):
  """
  Transforms underlying structures and types from GET_VIRTUAL_DISK_INFO to something human-readable.

  :param member_name:
  :param value:
  :return:
  """
  if member_name == 'ProviderSubtype':
    return ProviderSubtype.from_code(value)
  elif member_name == 'VirtualStorageType':
    return VirtualStorageType.from_code(value.DeviceId)
  elif member_name in ('IsLoaded', 'Enabled', 'IsRemote', 'ParentResolved', 'Is4kAligned', 'NewerChanges'):
    return bool(value)
  elif isinstance(value, GUID):
    return str(value)
  elif hasattr(value, "_fields_"):
    result = {}
    for field_name, _ in value._fields_:
      result[field_name] = transform_property(field_name, getattr(value, field_name))
    return result
  return value


class VHDDisk(object):
  def __init__(self, disk_path):
    self.disk_path = disk_path
    _ = self.properties

  @property
  def properties(self):
    return {name: transform_property(name, value) for name, value in get_vhd_info(self.disk_path).items()}

  def clone(self, clone_path, differencing=True):
    """
    Creates clone of current vhd disk.

    :param clone_path: path where cloned disk will be stored
    :param differencing: indicates if disk must be thin-copy
    :return: resulting VHDDisk
    """
    if differencing:
      close_handle(create_vhd(clone_path, parent_path=self.disk_path))
    else:
      close_handle(create_vhd(clone_path, src_path=self.disk_path))
    return VHDDisk(clone_path)
