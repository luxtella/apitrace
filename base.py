##########################################################################
#
# Copyright 2008-2009 VMware, Inc.
# All Rights Reserved.
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
#
##########################################################################/

"""C basic types"""


import debug


all_types = {}


class Visitor:

    def visit(self, type, *args, **kwargs):
        return type.visit(self, *args, **kwargs)

    def visit_void(self, void, *args, **kwargs):
        raise NotImplementedError

    def visit_literal(self, literal, *args, **kwargs):
        raise NotImplementedError

    def visit_string(self, string, *args, **kwargs):
        raise NotImplementedError

    def visit_const(self, const, *args, **kwargs):
        raise NotImplementedError

    def visit_struct(self, struct, *args, **kwargs):
        raise NotImplementedError

    def visit_array(self, array, *args, **kwargs):
        raise NotImplementedError

    def visit_blob(self, blob, *args, **kwargs):
        raise NotImplementedError

    def visit_enum(self, enum, *args, **kwargs):
        raise NotImplementedError

    def visit_bitmask(self, bitmask, *args, **kwargs):
        raise NotImplementedError

    def visit_pointer(self, pointer, *args, **kwargs):
        raise NotImplementedError

    def visit_handle(self, handle, *args, **kwargs):
        raise NotImplementedError

    def visit_alias(self, alias, *args, **kwargs):
        raise NotImplementedError

    def visit_opaque(self, opaque, *args, **kwargs):
        raise NotImplementedError

    def visit_interface(self, interface, *args, **kwargs):
        raise NotImplementedError


class OnceVisitor(Visitor):

    def __init__(self):
        self.__visited = set()

    def visit(self, type, *args, **kwargs):
        if type not in self.__visited:
            self.__visited.add(type)
            return type.visit(self, *args, **kwargs)
        return None


class Rebuilder(Visitor):

    def visit_void(self, void):
        return void

    def visit_literal(self, literal):
        return literal

    def visit_string(self, string):
        return string

    def visit_const(self, const):
        return Const(const.type)

    def visit_struct(self, struct):
        members = [self.visit(member) for member in struct.members]
        return Struct(struct.name, members)

    def visit_array(self, array):
        type = self.visit(array.type)
        return Array(type, array.length)

    def visit_blob(self, blob):
        type = self.visit(blob.type)
        return Blob(type, blob.size)

    def visit_enum(self, enum):
        return enum

    def visit_bitmask(self, bitmask):
        type = self.visit(bitmask.type)
        return Bitmask(type, bitmask.values)

    def visit_pointer(self, pointer):
        type = self.visit(pointer.type)
        return Pointer(type)

    def visit_handle(self, handle):
        type = self.visit(handle.type)
        return Handle(handle.name, type)

    def visit_alias(self, alias):
        type = self.visit(alias.type)
        return Alias(alias.expr, type)

    def visit_opaque(self, opaque):
        return opaque


class Type:

    __seq = 0

    def __init__(self, expr, id = ''):
        self.expr = expr
        
        for char in id:
            assert char.isalnum() or char in '_ '

        id = id.replace(' ', '_')
        
        if id in all_types:
            Type.__seq += 1
            id += str(Type.__seq)
        
        assert id not in all_types
        all_types[id] = self

        self.id = id

    def __str__(self):
        return self.expr

    def visit(self, visitor, *args, **kwargs):
        raise NotImplementedError



class _Void(Type):

    def __init__(self):
        Type.__init__(self, "void")

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_void(self, *args, **kwargs)

Void = _Void()


class Concrete(Type):

    def decl(self):
        print 'static void Dump%s(const %s &value);' % (self.id, self.expr)
    
    def impl(self):
        print 'static void Dump%s(const %s &value) {' % (self.id, self.expr)
        self._dump("value");
        print '}'
        print
    
    def _dump(self, instance):
        raise NotImplementedError
    
    def dump(self, instance):
        print '    Dump%s(%s);' % (self.id, instance)
    

class Literal(Type):

    def __init__(self, expr, format, base=10):
        Type.__init__(self, expr)
        self.format = format

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_literal(self, *args, **kwargs)


class Const(Type):

    def __init__(self, type):

        if type.expr.startswith("const "):
            expr = type.expr + " const"
        else:
            expr = "const " + type.expr

        Type.__init__(self, expr, 'C' + type.id)

        self.type = type

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_const(self, *args, **kwargs)


class Pointer(Type):

    def __init__(self, type):
        Type.__init__(self, type.expr + " *", 'P' + type.id)
        self.type = type

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_pointer(self, *args, **kwargs)


class Handle(Type):

    def __init__(self, name, type):
        Type.__init__(self, type.expr, 'P' + type.id)
        self.name = name
        self.type = type

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_handle(self, *args, **kwargs)


def ConstPointer(type):
    return Pointer(Const(type))


class Enum(Concrete):

    def __init__(self, name, values):
        Concrete.__init__(self, name)
        self.values = values
    
    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_enum(self, *args, **kwargs)


def FakeEnum(type, values):
    return Enum(type.expr, values)


class Bitmask(Concrete):

    def __init__(self, type, values):
        Concrete.__init__(self, type.expr)
        self.type = type
        self.values = values

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_bitmask(self, *args, **kwargs)

Flags = Bitmask


class Array(Type):

    def __init__(self, type, length):
        Type.__init__(self, type.expr + " *")
        self.type = type
        self.length = length

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_array(self, *args, **kwargs)


class Blob(Type):

    def __init__(self, type, size):
        Type.__init__(self, type.expr + ' *')
        self.type = type
        self.size = size

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_blob(self, *args, **kwargs)


class Struct(Concrete):

    def __init__(self, name, members):
        Concrete.__init__(self, name)
        self.name = name
        self.members = members

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_struct(self, *args, **kwargs)


class Alias(Type):

    def __init__(self, expr, type):
        Type.__init__(self, expr)
        self.type = type

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_alias(self, *args, **kwargs)


def Out(type, name):
    arg = Arg(type, name, output=True)
    return arg


class Arg:

    def __init__(self, type, name, output=False):
        self.type = type
        self.name = name
        self.output = output

    def __str__(self):
        return '%s %s' % (self.type, self.name)


class Function:

    def __init__(self, type, name, args, call = '', fail = None, sideeffects=True, hidden=False):
        self.type = type
        self.name = name

        self.args = []
        for arg in args:
            if isinstance(arg, tuple):
                arg_type, arg_name = arg
                arg = Arg(arg_type, arg_name)
            self.args.append(arg)

        self.call = call
        self.fail = fail
        self.sideeffects = sideeffects
        self.hidden = False

    def prototype(self, name=None):
        if name is not None:
            name = name.strip()
        else:
            name = self.name
        s = name
        if self.call:
            s = self.call + ' ' + s
        if name.startswith('*'):
            s = '(' + s + ')'
        s = self.type.expr + ' ' + s
        s += "("
        if self.args:
            s += ", ".join(["%s %s" % (arg.type, arg.name) for arg in self.args])
        else:
            s += "void"
        s += ")"
        return s


def StdFunction(*args, **kwargs):
    kwargs.setdefault('call', 'GLAPIENTRY')
    return Function(*args, **kwargs)


def FunctionPointer(type, name, args, **kwargs):
    # XXX
    return Opaque(name)


class Interface(Type):

    def __init__(self, name, base=None):
        Type.__init__(self, name)
        self.name = name
        self.base = base
        self.methods = []

    def itermethods(self):
        if self.base is not None:
            for method in self.base.itermethods():
                yield method
        for method in self.methods:
            yield method
        raise StopIteration


class Method(Function):

    def __init__(self, type, name, args):
        Function.__init__(self, type, name, args, call = '__stdcall')


towrap = []


def WrapPointer(type):
    return Pointer(type)


class _String(Type):

    def __init__(self):
        Type.__init__(self, "char *")

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_string(self, *args, **kwargs)

String = _String()


class Opaque(Type):
    '''Opaque pointer.'''

    def __init__(self, expr):
        Type.__init__(self, expr)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_opaque(self, *args, **kwargs)


def OpaquePointer(type):
    return Opaque(type.expr + ' *')



class API:

    def __init__(self, name):
        self.name = name
        self.headers = []
        self.types = set()
        self.functions = []
        self.interfaces = []

    def add_type(self, type):
        if type not in self.types:
            self.types.add(type)

    def add_function(self, function):
        self.functions.append(function)
        for arg in function.args:
            self.add_type(arg.type)
        self.add_type(function.type)

    def add_functions(self, functions):
        for function in functions:
            self.add_function(function)

    def add_interface(self, interface):
        self.interfaces.append(interface)

    def add_interfaces(self, interfaces):
        self.interfaces.extend(interfaces)


Bool = Literal("bool", "Bool")
SChar = Literal("signed char", "SInt")
UChar = Literal("unsigned char", "UInt")
Short = Literal("short", "SInt")
Int = Literal("int", "SInt")
Long = Literal("long", "SInt")
LongLong = Literal("long long", "SInt")
UShort = Literal("unsigned short", "UInt")
UInt = Literal("unsigned int", "UInt")
ULong = Literal("unsigned long", "UInt")
ULongLong = Literal("unsigned long long", "UInt")
Float = Literal("float", "Float")
Double = Literal("double", "Float")
SizeT = Literal("size_t", "UInt")
WString = Literal("wchar_t *", "WString")

