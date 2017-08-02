## Hyper-V management python library

This small python library utilize Hyper-V WMI api to provide simple synchronous and asyncio-compatible python api for 
creation and management of Hyper-V virtual machines.

## Internal Design

All operations performed via `pythonnet` bindings. This allows to call `.Net` assemblies from python just like they are
native python modules. This library utilize `System.Management` assembly and `root\virtualization\v2` namespace.

## Roadmap

* ~~switch to some wmi library(most likely it will be native **.Net Microsoft.Management**  via **pythonnet** bindings, it
works faster than native python **wmi** package)~~ - done
* refactor and document internal code to make is simpler to extend library
* add auto-generated documentation
* unit tests(maybe)

## License

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
