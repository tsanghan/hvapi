import time

from hvapi.clr.types import Msvm_ConcreteJob_JobState, VSMS_ModifyResourceSettings_ReturnCode, \
  VSMS_ModifySystemSettings_ReturnCode, VSMS_AddResourceSettings_ReturnCode
from hvapi.clr.base import JobException, ManagementObject
from hvapi.clr.invoke import evaluate_invocation_result


class JobWrapper(ManagementObject):
  MO_CLS = ('Msvm_ConcreteJob', 'Msvm_StorageJob')

  def wait(self):
    job_state = Msvm_ConcreteJob_JobState.from_code(self.properties['JobState'])
    while job_state not in [Msvm_ConcreteJob_JobState.Completed, Msvm_ConcreteJob_JobState.Terminated,
                            Msvm_ConcreteJob_JobState.Killed, Msvm_ConcreteJob_JobState.Exception]:
      job_state = Msvm_ConcreteJob_JobState.from_code(self.properties['JobState'])
      self.reload()
      time.sleep(.1)
    if job_state != Msvm_ConcreteJob_JobState.Completed:
      raise JobException(self)


class VirtualSystemManagementService(ManagementObject):
  MO_CLS = 'Msvm_VirtualSystemManagementService'

  def SetGuestNetworkAdapterConfiguration(self, ComputerSystem, *args):
    out_objects = self.invoke("SetGuestNetworkAdapterConfiguration", ComputerSystem=ComputerSystem,
                              NetworkConfiguration=args)
    return evaluate_invocation_result(
      out_objects,
      VSMS_ModifyResourceSettings_ReturnCode,
      VSMS_ModifyResourceSettings_ReturnCode.Completed_with_No_Error,
      VSMS_ModifyResourceSettings_ReturnCode.Method_Parameters_Checked_Job_Started
    )

  def ModifyResourceSettings(self, *args):
    out_objects = self.invoke("ModifyResourceSettings", ResourceSettings=args)
    return evaluate_invocation_result(
      out_objects,
      VSMS_ModifyResourceSettings_ReturnCode,
      VSMS_ModifyResourceSettings_ReturnCode.Completed_with_No_Error,
      VSMS_ModifyResourceSettings_ReturnCode.Method_Parameters_Checked_Job_Started
    )

  def ModifySystemSettings(self, SystemSettings):
    out_objects = self.invoke("ModifySystemSettings", SystemSettings=SystemSettings)
    return evaluate_invocation_result(
      out_objects,
      VSMS_ModifySystemSettings_ReturnCode,
      VSMS_ModifySystemSettings_ReturnCode.Completed_with_No_Error,
      VSMS_ModifySystemSettings_ReturnCode.Method_Parameters_Checked_Job_Started
    )

  def AddResourceSettings(self, AffectedConfiguration, *args):
    out_objects = self.invoke("AddResourceSettings", AffectedConfiguration=AffectedConfiguration, ResourceSettings=args)
    return evaluate_invocation_result(
      out_objects,
      VSMS_AddResourceSettings_ReturnCode,
      VSMS_AddResourceSettings_ReturnCode.Completed_with_No_Error,
      VSMS_AddResourceSettings_ReturnCode.Method_Parameters_Checked_Job_Started
    )

  def DefineSystem(self, SystemSettings, ResourceSettings=[], ReferenceConfiguration=None):
    out_objects = self.invoke("DefineSystem", SystemSettings=SystemSettings, ResourceSettings=ResourceSettings,
                              ReferenceConfiguration=ReferenceConfiguration)
    return evaluate_invocation_result(
      out_objects,
      VSMS_AddResourceSettings_ReturnCode,
      VSMS_AddResourceSettings_ReturnCode.Completed_with_No_Error,
      VSMS_AddResourceSettings_ReturnCode.Method_Parameters_Checked_Job_Started
    )
