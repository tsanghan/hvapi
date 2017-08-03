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
from typing import Sequence

from hvapi.clr.imports import ManagementObject


class PropertyTransformer(object):
  """
  Class that transforms property value to valid 'ManagementObject' instance. This need to be passed to 'PropertyNode' object.
  """

  @staticmethod
  def transform(property_value, parent: ManagementObject) -> ManagementObject:
    raise NotImplementedError


class NullTransformer(PropertyTransformer):
  """
  Just returns value if it is 'ManagementObject' instance.
  """

  @staticmethod
  def transform(property_value, parent: ManagementObject) -> ManagementObject:
    if isinstance(property_value, ManagementObject):
      return property_value
    raise ValueError("Value is not an instance of 'ManagementObject'")


class ReferenceTransformer(PropertyTransformer):
  """
  Transforms WMI reference value to 'ManagementObject' instance.
  """

  @staticmethod
  def transform(property_value, parent: ManagementObject) -> ManagementObject:
    return ManagementObject(property_value)


class Selector(object):
  """
  Checks if 'ManagementObject' is suitable for us during traversal.
  """

  def is_acceptable(self, management_object: ManagementObject):
    raise NotImplementedError


class NullSelector(Selector):
  """
  Selector that accepts all objects.
  """

  def is_acceptable(self, management_object: ManagementObject):
    return True


class PropertiesSelector(Selector):
  """
  Selector that choose objects based on their property values.
  """

  def __init__(self, **kwargs):
    self.properties = kwargs

  def is_acceptable(self, management_object: ManagementObject):
    for property_name, expected_value in self.properties:
      if str(management_object.properties[property_name]) != str(expected_value):
        return False
    return True


class Node(object):
  """
  Object that used to get child items from given 'ManagementObject' during traversal.
  """

  def get_node_objects(self, management_object: ManagementObject):
    raise NotImplementedError


class PropertyNode(Node):
  """
  Gets 'ManagementObject' instances from property `property_name` values.
  """

  def __init__(self, property_name, transformer: PropertyTransformer = NullTransformer(), selector: Selector = NullSelector()):
    self.property_name = property_name
    self.transformer = transformer
    self.selector = selector

  def get_node_objects(self, management_object: ManagementObject):
    results = []
    val = management_object.Properties[self.property_name].Value
    if not val.GetType().IsArray:
      _result = self.transformer.transform(val, management_object)
      if self.selector.is_acceptable(_result):
        results.append(_result)
    else:
      for val_item in val:
        _result = self.transformer.transform(val_item, management_object)
        if self.selector.is_acceptable(_result):
          results.append(_result)
    return results


class RelatedNode(Node):
  """
  Gets 'ManagementObject' instances from property `GetRelated` method call.
  """

  def __init__(self, related_arguments, selector: Selector = NullSelector()):
    """

    :param related_arguments: arguments to be passed to `GetRelated` method call
    :param selector:
    """
    self.related_arguments = related_arguments
    self.selector = selector

  def get_node_objects(self, management_object: ManagementObject):
    results = []
    for rel_object in management_object.GetRelated(*self.related_arguments):
      if not management_object == rel_object:
        _result = rel_object
        if self.selector.is_acceptable(_result):
          results.append(_result)
    return results


class RelationshipNode(Node):
  """
  Gets 'ManagementObject' instances from property `GetRelationships` method call.
  """

  def __init__(self, relationship_arguments, selector: Selector = NullSelector()):
    """

    :param relationship_arguments: arguments to be passed to `GetRelationships` method call
    :param selector:
    """

    self.relationship_arguments = relationship_arguments
    self.selector = selector

  def get_node_objects(self, management_object: ManagementObject):
    results = []
    for rel_object in management_object.GetRelationships(*self.relationship_arguments):
      if not management_object == rel_object:
        _result = rel_object
        if self.selector.is_acceptable(_result):
          results.append(_result)
    return results


VirtualSystemSettingDataNode = RelatedNode(("Msvm_VirtualSystemSettingData", "Msvm_SettingsDefineState", None, None, "SettingData", "ManagedElement", False, None))


def recursive_traverse(traverse_path: Sequence[Node], parent: 'ManagementObject'):
  results = []
  if len(traverse_path) == 1:
    for obj in traverse_path[0].get_node_objects(parent):
      results.append([obj])
    return results
  else:
    for obj in traverse_path[0].get_node_objects(parent):
      for children in recursive_traverse(traverse_path[1:], obj):
        cur_res = [obj]
        cur_res.extend(children)
        results.append(cur_res)
    return results
