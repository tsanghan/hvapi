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
import collections
from typing import List, Sequence

from hvapi.clr.imports import Guid, CimType, String, ManagementScope, ObjectQuery, ManagementObjectSearcher, \
  ManagementClass, ManagementException, ManagementObject, Array
from hvapi.clr.invoke import transform_argument
from hvapi.clr.traversal import Node, recursive_traverse
from hvapi.common import opencls


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


@opencls(ManagementScope)
class ManagementScope(object):
  def query(self, query, parent=None) -> List['ManagementObject']:
    result = []
    query_obj = ObjectQuery(query)
    searcher = ManagementObjectSearcher(self, query_obj)
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
    cls = ManagementClass(str(self.Path) + ":" + class_name)
    return cls.CreateInstance()


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


@opencls(ManagementObject)
class ManagementObject(object):
  def concrete_cls(self, cls):
    if not issubclass(cls, ManagementObject):
      raise ValueError("Class '{0}' is not and subclass of 'ManagementObject'".format(cls.__name__))
    if hasattr(cls, "MO_CLS"):
      mo_cls = getattr(cls, "MO_CLS")
      if self.ClassPath.ClassName not in mo_cls:
        raise ValueError('Given ManagementObject is not %s' % mo_cls)
      return cls(self.Path)
    else:
      raise ValueError("Class '{0}' does not contain 'MO_CLS' record".format(cls.__name__))

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

  def get_child(self, traverse_path: Sequence[Node]) -> ManagementObject:
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
    parameters = self.GetMethodParameters(method_name)
    for parameter in parameters.Properties:
      parameter_name = parameter.Name
      parameter_type = CimTypeTransformer.target_class(parameter.Type)

      if parameter_name not in kwargs:
        raise ValueError("Parameter '%s' not provided" % parameter_name)

      if parameter.IsArray:
        if not isinstance(kwargs[parameter_name], collections.Iterable):
          raise ValueError("Parameter '%s' must be iterable" % parameter_name)
        array_items = [transform_argument(item, parameter_type) for item in kwargs[parameter_name]]
        if array_items:
          parameter_value = Array[parameter_type](array_items)
        else:
          parameter_value = None
      else:
        parameter_value = transform_argument(kwargs[parameter_name], parameter_type)

      parameters.Properties[parameter_name].Value = parameter_value

    invocation_result = self.InvokeMethod(method_name, parameters, None)
    transformed_result = {}
    for _property in invocation_result.Properties:
      _property_type = CimTypeTransformer.target_class(_property.Type)
      _property_value = None
      if _property.Value is not None:
        if _property.IsArray:
          _property_value = [transform_argument(item, _property_type) for item in _property.Value]
        else:
          _property_value = transform_argument(_property.Value, _property_type)
      transformed_result[_property.Name] = _property_value
    return transformed_result

  def clone(self):
    return self.Clone()

  def __str__(self):
    return str(self)
