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
import logging
import time
from typing import List, Dict, Any

from hvapi._private import VirtualSystemManagementService, MOWrapper
from hvapi.clr.base import generate_guid, ManagementScope
from hvapi.clr.imports import clr_Array, clr_String
from hvapi.clr.invoke import evaluate_invocation_result
from hvapi.clr.traversal import ReferenceTransformer, PropertiesSelector, PropertyNode, RelatedNode, RelationshipNode, \
  VirtualSystemSettingDataNode
from hvapi.clr.types import (ComputerSystem_RequestStateChange_RequestedState,
                             ComputerSystem_RequestStateChange_ReturnCodes, ComputerSystem_EnabledState,
                             ShutdownComponent_OperationalStatus, ShutdownComponent_ShutdownComponent_ReturnCodes)
from hvapi.disk.vhd import VHDDisk
from hvapi.types import VirtualMachineGeneration, VirtualMachineState, ComPort, NotFoundException, TooManyResultsException

DEFAULT_WAIT_OP_TIMEOUT = 60


class VirtualSwitch(MOWrapper):
  MO_CLS = 'Msvm_VirtualEthernetSwitch'

  @property
  def name(self):
    return self.properties['ElementName']

  @property
  def id(self):
    return self.properties['Name']

  def __eq__(self, other):
    if other:
      return self.id == other.id and self.name == other.name


class AdapterGuestSettings(MOWrapper):
  """
  Class for managing virtual adapter guest settings. Can be used to inject static or dhcp ip settings.
  """
  MO_CLS = 'Msvm_GuestNetworkAdapterConfiguration'

  @property
  def dhcp(self):
    return self.properties['DHCPEnabled']

  @property
  def ip(self):
    return self.properties['IPAddresses']

  def set_ip_settings(self, dhcp=True, ip=[], sub_nets=[], gateways=[], dns=[]):
    management_service = VirtualSystemManagementService(self.Scope.query_one('SELECT * FROM Msvm_VirtualSystemManagementService'))
    self.properties.DHCPEnabled = dhcp
    self.properties.IPAddresses = ip
    self.properties.Subnets = sub_nets
    self.properties.DefaultGateways = gateways
    self.properties.DNSServers = dns
    self.properties.ProtocolIFType = 4096
    computer_system = self.parent.parent
    management_service.SetGuestNetworkAdapterConfiguration(computer_system, self)


class VirtualNetworkAdapter(MOWrapper):
  MO_CLS = 'Msvm_SyntheticEthernetPortSettingData'

  @property
  def address(self) -> str:
    return self.properties['Address']

  @property
  def switch(self) -> 'VirtualSwitch':
    result = []
    port_to_switch_path = (
      RelatedNode(("Msvm_EthernetPortAllocationSettingData",)),
      PropertyNode("HostResource", transformer=ReferenceTransformer())
    )
    for _, virtual_switch in self.traverse(port_to_switch_path):
      result.append(VirtualSwitch(virtual_switch))
    if len(result) > 1:
      raise Exception("Something horrible happened, virtual network adapter connected to more that one virtual switch")
    if result:
      return result[0]
    return None

  def guest_settings(self) -> AdapterGuestSettings:
    """
    Returns instance of AdapterGuestSettings.

    :return: associated AdapterGuestSettings with given adapter
    """
    settings_path = (
      RelatedNode(("Msvm_GuestNetworkAdapterConfiguration",)),
    )
    return AdapterGuestSettings(self.get_child(settings_path), self)

  def connect(self, virtual_switch: 'VirtualSwitch'):
    """
    Connect adapter to given virtual switch.

    :param virtual_switch: virtual switch to connect
    """
    management_service = VirtualSystemManagementService(self.Scope.query_one('SELECT * FROM Msvm_VirtualSystemManagementService'))
    Msvm_VirtualSystemSettingData = self.traverse((RelatedNode(("Msvm_VirtualSystemSettingData",)),))[-1][-1]
    Msvm_ResourcePool = self.Scope.query_one("SELECT * FROM Msvm_ResourcePool WHERE ResourceSubType = 'Microsoft:Hyper-V:Ethernet Connection' AND Primordial = True")
    Msvm_EthernetPortAllocationSettingData_Path = (
      RelatedNode(("Msvm_AllocationCapabilities", "Msvm_ElementCapabilities", None, None, None, None, False, None)),
      RelationshipNode(("Msvm_SettingsDefineCapabilities",), selector=PropertiesSelector(ValueRole=0)),
      PropertyNode("PartComponent", transformer=ReferenceTransformer())
    )
    Msvm_EthernetPortAllocationSettingData = \
      Msvm_ResourcePool.traverse(Msvm_EthernetPortAllocationSettingData_Path)[-1][-1]
    Msvm_EthernetPortAllocationSettingData.properties.Parent = self
    Msvm_EthernetPortAllocationSettingData.properties.HostResource = [virtual_switch]
    management_service.AddResourceSettings(Msvm_VirtualSystemSettingData, Msvm_EthernetPortAllocationSettingData)


class VirtualComPort(MOWrapper):
  MO_CLS = 'Msvm_SerialPortSettingData'

  @property
  def name(self) -> str:
    return self.properties.ElementName

  @property
  def path(self) -> str:
    if len(self.properties.Connection) > 0:
      return self.properties.Connection[0]

  @path.setter
  def path(self, value):
    management_service = VirtualSystemManagementService(self.Scope.query_one('SELECT * FROM Msvm_VirtualSystemManagementService'))
    self.properties.Connection = [value]
    management_service.ModifyResourceSettings(self)


class ShutdownComponent(MOWrapper):
  MO_CLS = 'Msvm_ShutdownComponent'

  def InitiateShutdown(self, Force, Reason):
    out_objects = self.invoke("InitiateShutdown", Force=Force, Reason=Reason)
    return evaluate_invocation_result(
      out_objects,
      ShutdownComponent_ShutdownComponent_ReturnCodes,
      ShutdownComponent_ShutdownComponent_ReturnCodes.Completed_with_No_Error,
      ShutdownComponent_ShutdownComponent_ReturnCodes.Method_Parameters_Checked_JobStarted
    )

# TODO expose cpu, memory, etc settings via properties
class VirtualMachine(MOWrapper):
  """
  Represents virtual machine. Gives access to machine name and id, network adapters, gives ability to start,
  stop, pause, save, reset machine.
  """
  LOG = logging.getLogger('%s.%s' % (__module__, __qualname__))
  MO_CLS = 'Msvm_ComputerSystem'
  _CLS_MAP_PRIORITY = {
    "Msvm_VirtualSystemSettingData": 0
  }
  PATH_MAP = {
    "Msvm_ProcessorSettingData": (
      VirtualSystemSettingDataNode,
      RelatedNode(("Msvm_ProcessorSettingData",))
    ),
    "Msvm_MemorySettingData": (
      VirtualSystemSettingDataNode,
      RelatedNode(("Msvm_MemorySettingData",)),
    ),
    "Msvm_VirtualSystemSettingData": (
      VirtualSystemSettingDataNode,
    )
  }
  RESOURCE_CLASSES = ("Msvm_ProcessorSettingData", "Msvm_MemorySettingData")
  SYSTEM_CLASSES = ("Msvm_VirtualSystemSettingData",)

  def apply_properties(self, class_name: str, properties: Dict[str, Any]):
    """
    Apply ``properties`` for ``class_name`` that associated with virtual machine.

    :param class_name: class name that will be used for modification
    :param properties: properties to apply
    """
    management_service = VirtualSystemManagementService(self.Scope.query_one('SELECT * FROM Msvm_VirtualSystemManagementService'))
    class_instance = self.traverse(self.PATH_MAP[class_name])[0][-1]
    for property_name, property_value in properties.items():
      setattr(class_instance.properties, property_name, property_value)
    if class_name in self.RESOURCE_CLASSES:
      management_service.ModifyResourceSettings(class_instance)
    if class_name in self.SYSTEM_CLASSES:
      management_service.ModifySystemSettings(SystemSettings=class_instance)

  def apply_properties_group(self, properties_group: Dict[str, Dict[str, Any]]):
    """
    Applies given properties to virtual machine.

    :param properties_group: dict of classes and their properties
    """
    if properties_group:
      for cls, properties in sorted(properties_group.items(), key=lambda itm: self._CLS_MAP_PRIORITY.get(itm[0], 100)):
        self.apply_properties(cls, properties)

  @property
  def name(self) -> str:
    """
    Virtual machine name that displayed everywhere in windows UI and other places.

    :return: virtual machine name
    """
    return self.properties['ElementName']

  @property
  def id(self) -> str:
    """
    Unique virtual machine identifier.

    :return: virtual machine identifier
    """
    return self.properties['Name']

  @property
  def state(self) -> VirtualMachineState:
    """
    Current virtual machine state. It will try to get actual real state(like running, stopped, etc) for
    ``DEFAULT_WAIT_OP_TIMEOUT`` seconds before returning ``VirtualMachineState.UNDEFINED``. We need this
    ``DEFAULT_WAIT_OP_TIMEOUT`` because hyper-v likes some middle states, like starting, stopping, etc.
    Usually this middle states long not more that 10 seconds and soon will changed to something that we expecting.

    :return: virtual machine state
    """
    _start = time.time()
    state = self._enabled_state.to_virtual_machine_state()
    while state == VirtualMachineState.UNDEFINED and time.time() - _start < DEFAULT_WAIT_OP_TIMEOUT:
      state = self._enabled_state.to_virtual_machine_state()
      time.sleep(.1)
    return state

  def start(self):
    """
    Try to start virtual machine and wait for started state for ``timeout`` seconds.
    """
    if self.state != VirtualMachineState.RUNNING:
      self.LOG.debug("Starting machine '%s'", self.id)
      desired_state = ComputerSystem_RequestStateChange_RequestedState.Running
      target_enabled_state = desired_state.to_ComputerSystem_EnabledState()
      self.RequestStateChange(desired_state)
      if not self._wait_for_enabled_state(target_enabled_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
        raise Exception("Failed to put machine to '%s' in %s seconds" % (target_enabled_state, DEFAULT_WAIT_OP_TIMEOUT))
      self.LOG.debug("Started machine '%s'", self.id)
    else:
      self.LOG.debug("Machine '%s' is already started", self.id)

  def stop(self, force=False, hard=False):
    """
    Try to stop virtual machine and wait for stopped state for ``timeout`` seconds.

    :param force: indicates if we need to wait for user programs completion, ignored if *force* is *True*
    :param hard: indicates if we need to perform turn off(power off)
    """
    self.LOG.debug("Stopping machine '%s'", self.id)
    desired_state = ComputerSystem_RequestStateChange_RequestedState.Off
    target_enabled_state = desired_state.to_ComputerSystem_EnabledState()
    if not hard:
      shutdown_component = self._get_shutdown_component()
      if shutdown_component:
        shutdown_component.InitiateShutdown(force, "hvapi shutdown")
        if not self._wait_for_enabled_state(target_enabled_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
          self.LOG.debug("Failed to stop machine '%s' gracefully, killing...", self.id)
          self.kill()
      else:
        self.LOG.debug("Graceful stop for machine '%s' not available, killing...", self.id)
        self.kill()
    else:
      self.kill()
    self.LOG.debug("Stopped machine '%s'", self.id)

  def kill(self):
    """
    Hard-kill vm.
    """
    desired_state = ComputerSystem_RequestStateChange_RequestedState.Off
    target_enabled_state = desired_state.to_ComputerSystem_EnabledState()
    self.RequestStateChange(desired_state)
    if not self._wait_for_enabled_state(target_enabled_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
      raise Exception("Failed to put machine to '%s' in %s seconds" % (target_enabled_state, DEFAULT_WAIT_OP_TIMEOUT))

  def save(self):
    """
    Try to save virtual machine state and wait for saved state for ``timeout`` seconds.
    """
    if self.state != VirtualMachineState.SAVED:
      self.LOG.debug("Saving machine '%s'", self.id)
      desired_state = ComputerSystem_RequestStateChange_RequestedState.Saved
      target_enabled_state = desired_state.to_ComputerSystem_EnabledState()
      self.RequestStateChange(desired_state)
      if not self._wait_for_enabled_state(target_enabled_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
        raise Exception("Failed to put machine to '%s' in %s seconds" % (target_enabled_state, DEFAULT_WAIT_OP_TIMEOUT))
      self.LOG.debug("Saved machine '%s'", self.id)
    else:
      self.LOG.debug("Machine '%s' is already saved", self.id)

  def pause(self):
    if self.state != VirtualMachineState.PAUSED:
      self.LOG.debug("Pausing machine '%s'", self.id)
      desired_state = ComputerSystem_RequestStateChange_RequestedState.Paused
      target_enabled_state = desired_state.to_ComputerSystem_EnabledState()
      self.RequestStateChange(desired_state)
      if not self._wait_for_enabled_state(target_enabled_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
        raise Exception("Failed to put machine to '%s' in %s seconds" % (target_enabled_state, DEFAULT_WAIT_OP_TIMEOUT))
      self.LOG.debug("Paused machine '%s'", self.id)
    else:
      self.LOG.debug("Machine '%s' is already paused", self.id)

  def add_adapter(self, static_mac=False, mac=None, adapter_name="Network Adapter") -> 'VirtualNetworkAdapter':
    """
    Add adapter to virtual machine.

    :param static_mac: make adapter with static mac
    :param mac: mac address t assign
    :param adapter_name: adapter name
    :return: created adapter
    """
    management_service = VirtualSystemManagementService(self.Scope.query_one('SELECT * FROM Msvm_VirtualSystemManagementService'))
    Msvm_ResourcePool = self.Scope.query_one(
      "SELECT * FROM Msvm_ResourcePool WHERE ResourceSubType = 'Microsoft:Hyper-V:Synthetic Ethernet Port' "
      "AND Primordial = True"
    )
    Msvm_SyntheticEthernetPortSettingData_Path = (
      RelatedNode(("Msvm_AllocationCapabilities", "Msvm_ElementCapabilities", None, None, None, None, False, None)),
      RelationshipNode(("Msvm_SettingsDefineCapabilities",), selector=PropertiesSelector(ValueRole=0)),
      PropertyNode("PartComponent", transformer=ReferenceTransformer())
    )
    Msvm_VirtualSystemSettingData = self.traverse((VirtualSystemSettingDataNode,))[-1][-1]
    Msvm_SyntheticEthernetPortSettingData = Msvm_ResourcePool.traverse(Msvm_SyntheticEthernetPortSettingData_Path)[-1][
      -1]
    Msvm_SyntheticEthernetPortSettingData.properties.VirtualSystemIdentifiers = clr_Array[clr_String]([generate_guid()])
    Msvm_SyntheticEthernetPortSettingData.properties.ElementName = adapter_name
    Msvm_SyntheticEthernetPortSettingData.properties.StaticMacAddress = static_mac
    if mac:
      Msvm_SyntheticEthernetPortSettingData.properties.Address = mac
    result = management_service.AddResourceSettings(Msvm_VirtualSystemSettingData,
                                                    Msvm_SyntheticEthernetPortSettingData)
    return VirtualNetworkAdapter(result['ResultingResourceSettings'][-1], self)

  def is_connected_to_switch(self, virtual_switch: 'VirtualSwitch'):
    """
    Returns ``True`` if machine is connected to given ``VirtualSwitch``.

    :param virtual_switch: virtual switch to check connection
    :return: ``True`` if connected, otherwise ``False``
    """
    for adapter in self.network_adapters:
      if virtual_switch == adapter.switch:
        return True

  def add_vhd_disk(self, vhd_disk: VHDDisk):
    """
    Adds given ``VHDDisk`` to virtual machine.

    :param vhd_disk: ``VHDDisk`` to add to machine
    """
    # TODO ability to select controller, disk port, error checking. Make disk bootable by default, etc
    management_service = VirtualSystemManagementService(self.Scope.query_one('SELECT * FROM Msvm_VirtualSystemManagementService'))
    Msvm_VirtualSystemSettingData = self.get_child((VirtualSystemSettingDataNode,))
    Msvm_ResourcePool_SyntheticDiskDrive = self.Scope.query_one(
      "SELECT * FROM Msvm_ResourcePool WHERE ResourceSubType = 'Microsoft:Hyper-V:Synthetic Disk Drive' AND Primordial = True")
    Msvm_StorageAllocationSettingData_Path = (
      RelatedNode(("Msvm_AllocationCapabilities", "Msvm_ElementCapabilities", None, None, None, None, False, None)),
      RelationshipNode(("Msvm_SettingsDefineCapabilities",), selector=PropertiesSelector(ValueRole=0)),
      PropertyNode("PartComponent", transformer=ReferenceTransformer())
    )
    IdeController_Path = (
      RelatedNode(("Msvm_ResourceAllocationSettingData",), selector=PropertiesSelector(ResourceType=5,
                                                                                       ResourceSubType='Microsoft:Hyper-V:Emulated IDE Controller',
                                                                                       Address=0)),
    )
    IdeController = Msvm_VirtualSystemSettingData.get_child(IdeController_Path)
    Msvm_StorageAllocationSettingData = Msvm_ResourcePool_SyntheticDiskDrive.get_child(
      Msvm_StorageAllocationSettingData_Path).clone()

    Msvm_StorageAllocationSettingData.properties.Parent = IdeController
    Msvm_StorageAllocationSettingData.properties.AddressOnParent = 0
    synthetic_disk_drive = \
      management_service.AddResourceSettings(Msvm_VirtualSystemSettingData, Msvm_StorageAllocationSettingData)[
        'ResultingResourceSettings'][-1]

    Msvm_ResourcePool_VirtualHardDisk = self.Scope.query_one(
      "SELECT * FROM Msvm_ResourcePool WHERE ResourceSubType = 'Microsoft:Hyper-V:Virtual Hard Disk' AND Primordial = True")
    virtual_hard_disk_path = (
      RelatedNode(("Msvm_AllocationCapabilities", "Msvm_ElementCapabilities", None, None, None, None, False, None)),
      RelationshipNode(("Msvm_SettingsDefineCapabilities",), selector=PropertiesSelector(ValueRole=0)),
      PropertyNode("PartComponent", transformer=ReferenceTransformer())
    )
    virtual_hard_disk_data = Msvm_ResourcePool_VirtualHardDisk.get_child(virtual_hard_disk_path).clone()
    virtual_hard_disk_data.properties.Parent = synthetic_disk_drive
    virtual_hard_disk_data.properties.HostResource = [vhd_disk.Path]
    management_service.AddResourceSettings(Msvm_VirtualSystemSettingData, virtual_hard_disk_data)

  @property
  def network_adapters(self) -> List[VirtualNetworkAdapter]:
    """
    Returns list of machines network adapters.

    :return: list of machines network adapters
    """
    result = []
    port_to_switch_path = (
      VirtualSystemSettingDataNode,
      RelatedNode(("Msvm_SyntheticEthernetPortSettingData",))
    )
    for _, Msvm_SyntheticEthernetPortSettingData in self.traverse(port_to_switch_path):
      result.append(VirtualNetworkAdapter(Msvm_SyntheticEthernetPortSettingData, self))
    return result

  @property
  def com_ports(self) -> List[VirtualComPort]:
    """
    Returns list of machine com-ports.

    :return: machine com-ports
    """
    result = []
    com_ports_path = (
      VirtualSystemSettingDataNode,
      RelatedNode(("Msvm_ResourceAllocationSettingData",),
                  selector=PropertiesSelector(ResourceSubtype="Microsoft:Hyper-V:Serial Controller")),
      RelatedNode(("Msvm_SerialPortSettingData",))
    )
    for _, _, Msvm_SerialPortSettingData in self.traverse(com_ports_path):
      result.append(VirtualComPort(Msvm_SerialPortSettingData, self))
    return result

  def get_com_port(self, port: ComPort):
    """
    Get concrete com-port

    :param port: port to get
    :return: concrete com-port
    """
    # TODO implement this via wmi
    return self.com_ports[port.value]

  # internal methods
  def _wait_for_enabled_state(self, awaitable_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
    _start = time.time()
    while self._enabled_state != awaitable_state and time.time() - _start < timeout:
      time.sleep(1)
    return self._enabled_state == awaitable_state

  def _get_shutdown_component(self):
    shutdown_component_traverse_result = self.traverse((RelatedNode(("Msvm_ShutdownComponent",)),))
    if shutdown_component_traverse_result:
      Msvm_ShutdownComponent = shutdown_component_traverse_result[-1][-1]
      operational_status = ShutdownComponent_OperationalStatus.from_code(Msvm_ShutdownComponent.properties['OperationalStatus'][0])
      if operational_status in (ShutdownComponent_OperationalStatus.OK, ShutdownComponent_OperationalStatus.Degraded):
        return ShutdownComponent(Msvm_ShutdownComponent)
    return None

  @property
  def _enabled_state(self) -> ComputerSystem_EnabledState:
    self.reload()
    return ComputerSystem_EnabledState.from_code(self.properties['EnabledState'])

  # WMI object methods
  def RequestStateChange(self, RequestedState: ComputerSystem_RequestStateChange_RequestedState, TimeoutPeriod=None):
    out_objects = self.invoke("RequestStateChange", RequestedState=RequestedState.value, TimeoutPeriod=TimeoutPeriod)
    return evaluate_invocation_result(
      out_objects,
      ComputerSystem_RequestStateChange_ReturnCodes,
      ComputerSystem_RequestStateChange_ReturnCodes.Completed_with_No_Error,
      ComputerSystem_RequestStateChange_ReturnCodes.Method_Parameters_Checked_Transition_Started
    )


class HypervHost(object):
  """
  Provides basic interface to get virtual machines, switches, and disk images for host.
  """

  def __init__(self, host="."):
    self.scope = ManagementScope(r"\\{0}\root\virtualization\v2".format(host))

  @property
  def switches(self) -> List[VirtualSwitch]:
    switches = self.scope.query('SELECT * FROM Msvm_VirtualEthernetSwitch')
    return [VirtualSwitch(_switch) for _switch in switches] if switches else []

  def switch_by_name(self, name) -> VirtualSwitch:
    switches = self.scope.query('SELECT * FROM Msvm_VirtualEthernetSwitch WHERE ElementName = "%s"' % name)
    if len(switches) == 0:
      raise NotFoundException("No switch with name {0}".format(name))
    if len(switches) > 1:
      raise TooManyResultsException("Too many switches with name {0}".format(name))
    return VirtualSwitch(switches[-1])

  def switch_by_id(self, switch_id) -> VirtualSwitch:
    switches = self.scope.query('SELECT * FROM Msvm_VirtualEthernetSwitch WHERE Name = "%s"' % switch_id)
    if len(switches) == 0:
      raise NotFoundException("No switch with id {0}".format(switch_id))
    if len(switches) > 1:
      raise TooManyResultsException("Too many switches with id {0}".format(switch_id))
    return VirtualSwitch(switches[-1])

  @property
  def machines(self) -> List[VirtualMachine]:
    machines = self.scope.query('SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine"')
    return [VirtualMachine(_machine) for _machine in machines] if machines else []

  def machine_by_name(self, name) -> VirtualMachine:
    machines = self.scope.query('SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine" AND ElementName = "%s"' % name)
    if len(machines) == 0:
      raise NotFoundException("No machine with name {0}".format(name))
    if len(machines) > 1:
      raise TooManyResultsException("Too many machines with name {0}".format(name))
    return VirtualMachine(machines[-1])

  def machine_by_id(self, machine_id) -> VirtualMachine:
    machines = self.scope.query('SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine" AND Name = "%s"' % machine_id)
    if len(machines) == 0:
      raise NotFoundException("No machine with id {0}".format(machine_id))
    if len(machines) > 1:
      raise TooManyResultsException("Too many machines with id {0}".format(machine_id))
    return VirtualMachine(machines[-1])

  def create_machine(self, name, properties_group: Dict[str, Dict[str, Any]] = None,
                     machine_generation: VirtualMachineGeneration = VirtualMachineGeneration.GEN1) -> VirtualMachine:
    management_service = VirtualSystemManagementService(self.scope.query_one('SELECT * FROM Msvm_VirtualSystemManagementService'))
    Msvm_VirtualSystemSettingData = self.scope.cls_instance("Msvm_VirtualSystemSettingData")
    Msvm_VirtualSystemSettingData.properties.ElementName = name
    Msvm_VirtualSystemSettingData.properties.VirtualSystemSubType = machine_generation.value
    result = management_service.DefineSystem(SystemSettings=Msvm_VirtualSystemSettingData)
    vm = VirtualMachine(result['ResultingSystem'])
    vm.apply_properties_group(properties_group)
    return vm
