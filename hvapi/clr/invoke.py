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
from hvapi.clr.base import ManagementObject, InvocationException
from hvapi.clr.imports import String
from hvapi.common import RangedCodeEnum


def transform_argument(obj, expected_type=None):
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


def evaluate_invocation_result(result, codes_enum: RangedCodeEnum, ok_value, job_value):
  """
  Evaluates invocation results from 'ManagementObject'. All method invocations returns object that contains return code
  ('ReturnValue' field), invocation result or reference for Job that need to be waited for to have some result.

  :param result:
  :param codes_enum:
  :param ok_value:
  :param job_value:
  :return:
  """
  return_value = codes_enum.from_code(result['ReturnValue'])
  if return_value == job_value:
    from hvapi._private import JobWrapper
    result['Job'].concrete_cls(JobWrapper).wait()
    return result
  if return_value != ok_value:
    raise InvocationException("Failed execute method with return value '%s'" % return_value.name)
  return result
