"""
The MIT License

Copyright (c) 2017 Eugene Chekanskiy, echekanskiy@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import logging
import uuid
import os
from hvapi.hyperv import HypervHost
from hvapi.disk.vhd import VHDDisk, VirtualStorageType

FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

original_disk_path = r"C:\Users\evhenii\Desktop\centos7\centos7\Virtual Hard Disks\centos7.vhdx"
original_disk = VHDDisk(original_disk_path)


def clone_disk(disk: VHDDisk):
  if disk.properties['VirtualStorageType'] == VirtualStorageType.VHDX:
    clone_disk_path = os.path.join(os.path.dirname(original_disk_path), str(uuid.uuid4()) + ".vhdx")
  else:
    clone_disk_path = os.path.join(os.path.dirname(original_disk_path), str(uuid.uuid4()) + ".vhd")

  return disk.clone(clone_disk_path)


machines = [
  ("c7.001", "192.168.55.101"),
  ("c7.002", "192.168.55.102"),
  ("c7.003", "192.168.55.103")
]
default_configuration = {
  "Msvm_ProcessorSettingData": {
    "VirtualQuantity": 3
  },
  "Msvm_VirtualSystemSettingData": {
    "VirtualNumaEnabled": False
  },
  "Msvm_MemorySettingData": {
    "DynamicMemoryEnabled": True,
    "Reservation": 256,
    "VirtualQuantity": 2048,
    "Limit": 8096
  }
}
host = HypervHost()
switch = host.switch_by_name("internal")
for name, ip in machines:
  vm = host.create_machine(name, default_configuration)
  adapter = vm.add_adapter()
  adapter.connect(switch)
  adapter.guest_settings().set_ip_settings(False, [ip], ["255.255.255.0"], ["192.168.55.1"], ["8.8.8.8"])
  vm.add_vhd_disk(clone_disk(original_disk))
