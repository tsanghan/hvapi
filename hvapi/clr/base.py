import collections
from typing import List, Sequence

from hvapi.clr.imports import Guid, CimType, String, ManagementScope, ObjectQuery, ManagementObjectSearcher, ManagementClass, ManagementException, ManagementObject, Array
from hvapi.clr.traversal import Node, recursive_traverse
from hvapi.common_types import RangedCodeEnum


def generate_guid(fmt="B"):
  return Guid.NewGuid().ToString(fmt)


class CimTypeTransformer(object):
  """

  """

  @staticmethod
  def target_class(value):
    """
    Returns target class in witch given CimType can/must be transformed.

    :param value: System.Management.CimType enum item
    :return: target class
    """
    if value == CimType.String:
      return String
    if value == CimType.Reference:
      return ManagementObject
    if value in (CimType.UInt32, CimType.UInt16):
      return int
    if value == CimType.DateTime:
      return String
    if value == CimType.Boolean:
      return bool
    raise Exception("unknown type")


class ScopeHolder(object):
  def __init__(self, namespace=r"\\.\root\virtualization\v2"):
    self.scope = ManagementScope(namespace)

  def query(self, query, parent=None) -> List['ManagementObject']:
    result = []
    query_obj = ObjectQuery(query)
    searcher = ManagementObjectSearcher(self.scope, query_obj)
    for man_object in searcher.Get():
      result.append(man_object)
    return result

  def query_one(self, query) -> 'ManagementObject':
    result = self.query(query)
    if len(result) > 1:
      raise Exception("Got too many results for query '%s'" % query)
    if result:
      return result[0]

  def cls_instance(self, class_name):
    cls = ManagementClass(str(self.scope.Path) + ":" + class_name)
    return cls.CreateInstance()


class JobException(Exception):
  def __init__(self, job):
    msg = "Job code:'%s' status:'%s' description:'%s'" % (
      job.properties.ErrorCode, job.properties.JobStatus, job.properties.ErrorDescription)
    super().__init__(msg)


class InvocationException(Exception):
  pass


class PropertiesHolder(object):
  def __init__(self, management_object):
    self.management_object = management_object

  def __getattribute__(self, key):
    if key != 'management_object':
      try:
        return self.management_object.Properties[key].Value
      except ManagementException as e:
        pass
    return super().__getattribute__(key)

  def __setattr__(self, key, value):
    if key != 'management_object':
      try:
        self.management_object.Properties[key].Value = value
      except ManagementException:
        pass
      except AttributeError:
        pass
    super().__setattr__(key, value)

  def __getitem__(self, item):
    return self.management_object.Properties[item].Value


def opencls(cls):
  def update(extension):
    for k, v in extension.__dict__.items():
      if k != '__dict__':
        try:
          setattr(cls, k, v)
        except AttributeError as e:
          if "attribute is read-only" in str(e):
            pass
          else:
            raise
    return cls

  return update


@opencls(ManagementObject)
class ManagementObject(object):
  def reload(self):
    self.Get()

  @property
  def properties(self):
    return PropertiesHolder(self)

  @property
  def properties_dict(self):
    result = {}
    for _property in self.Properties:
      result[_property.Name] = _property.Value
    return result

  def traverse(self, traverse_path: Sequence[Node]) -> List[List[ManagementObject]]:
    """
    Traverse through management object hierarchy based on given path.
    Return all found path from given object to target object.

    :param traverse_path:
    :return: list of found paths
    """
    return recursive_traverse(traverse_path, self)

  def get_child(self, traverse_path: Sequence[Node]):
    """
    Get one child item from given path.

    :param traverse_path:
    :return:
    """
    traverse_result = self.traverse(traverse_path)
    if len(traverse_result) > 1:
      raise Exception("Found more that one child for given path")
    return traverse_result[-1][-1]

  def invoke(self, method_name, **kwargs):
    parameters = self.management_object.GetMethodParameters(method_name)
    for parameter in parameters.Properties:
      parameter_name = parameter.Name
      parameter_type = CimTypeTransformer.target_class(parameter.Type)

      if parameter_name not in kwargs:
        raise ValueError("Parameter '%s' not provided" % parameter_name)

      if parameter.IsArray:
        if not isinstance(kwargs[parameter_name], collections.Iterable):
          raise ValueError("Parameter '%s' must be iterable" % parameter_name)
        array_items = [self.invoke_transform_object(item, parameter_type) for item in kwargs[parameter_name]]
        if array_items:
          parameter_value = Array[parameter_type](array_items)
        else:
          parameter_value = None
      else:
        parameter_value = self.invoke_transform_object(kwargs[parameter_name], parameter_type)

      parameters.Properties[parameter_name].Value = parameter_value

    invocation_result = self.management_object.InvokeMethod(method_name, parameters, None)
    transformed_result = {}
    for _property in invocation_result.Properties:
      _property_type = CimTypeTransformer.target_class(_property.Type)
      _property_value = None
      if _property.Value is not None:
        if _property.IsArray:
          _property_value = [self.invoke_transform_object(item, _property_type) for item in _property.Value]
        else:
          _property_value = self.invoke_transform_object(_property.Value, _property_type)
      transformed_result[_property.Name] = _property_value
    return transformed_result

  def clone(self):
    return self.Clone()

  def __str__(self):
    return str(self.management_object)

  # TODO move invoke static stuff to separate fle
  @staticmethod
  def invoke_transform_object(obj, expected_type=None):
    """
    Transforms input object to expected type.

    :param obj:
    :param expected_type:
    :return:
    """
    if obj is None:
      return None

    # management object to something that can be passed to function call
    if isinstance(obj, ManagementObject):
      if expected_type == String:
        return String(obj.GetText(2))
      if expected_type == ManagementObject:
        return obj
      raise ValueError("Object '%s' can not be transformed to '%s'" % (obj, expected_type))

    if isinstance(obj, (String, str)):
      if expected_type == ManagementObject:
        return ManagementObject(obj)

    if isinstance(obj, int):
      if expected_type == int:
        return obj

    if isinstance(obj, bool):
      if expected_type == bool:
        return obj

    if isinstance(obj, (str, String)):
      if expected_type == String:
        return String(obj)

    raise Exception("Unknown object to transform: '%s'" % obj)

  @staticmethod
  def _evaluate_invocation_result(result, codes_enum: RangedCodeEnum, ok_value, job_value):
    return_value = codes_enum.from_code(result['ReturnValue'])
    if return_value == job_value:
      from hvapi.clr.classes_wrappers import JobWrapper
      JobWrapper.from_moh(result['Job']).wait()
      return result
    if return_value != ok_value:
      raise InvocationException("Failed execute method with return value '%s'" % return_value.name)
    return result
