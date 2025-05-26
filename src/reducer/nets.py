"""Interaction nets.

Each node has multiple port attributes, each port attribute's value is a
(node, port type) pair.

"""

from pomagma.util import TODO

# ----------------------------------------------------------------------------
# Net data structure


class Node(object):
    def validate(self):
        """Asserts that node's neighbors point back to node."""
        if __debug__:
            node_0 = self
            for port_0 in node_0.ports:
                assert hasattr(node_0, port_0)
                node_1, port_1 = getattr(node_0, port_0)
                assert hasattr(node_1, port_1)
                node_2, port_2 = getattr(node_1, port_1)
                assert node_2 == node_0, (node_2, node_0)
                assert port_2 == port_0, (port_2, port_0)


class ROOT(Node):
    ports = ["root"]
    __slots__ = ports


class VAR(Node):
    """VARs are used only during net construction."""

    ports = ["val"]
    __slots__ = ["name"] + ports

    def __init__(self, name):
        self.name = name


class APP(Node):
    ports = ["fun", "arg", "val"]
    __slots__ = ports


class ABS(Node):
    ports = ["var", "body", "val"]
    __slots__ = ports


class COPY(Node):
    """Copy nodes have ids as in https://arxiv.org/pdf/1701.04691.pdf"""

    ports = ["lhs", "rhs", "val"]
    __slots__ = ["id"] + ports

    def __init__(self, id):
        self.id = id


class ERASE(Node):
    ports = ["val"]
    __slots__ = ports


class Net(set):
    def __init__(self):
        self.root = self.make(ROOT)

    def make(self, cls, *args):
        """Make a new node cls(*args) and add it to self."""
        assert issubclass(cls, Node)
        node = cls(*args)
        self.add(node)
        return node

    def validate(self):
        if __debug__:
            assert self.root in self
            for node in self:
                node.validate()
                if isinstance(node, ROOT):
                    assert node is self.root


# ----------------------------------------------------------------------------
# Interactions


def connect(lhs, rhs):
    assert isinstance(lhs, tuple) and len(lhs) == 2
    assert isinstance(rhs, tuple) and len(rhs) == 2
    assert isinstance(lhs[0], Node) and isinstance(lhs[1], str)
    assert isinstance(rhs[0], Node) and isinstance(rhs[1], str)
    setattr(lhs[0], lhs[1], rhs)
    setattr(rhs[0], rhs[1], lhs)


def interact_copy_app(net, app, copy):
    assert isinstance(net, Net)
    assert isinstance(app, APP)
    assert isinstance(copy, COPY)
    assert app.fun == (copy, "val")
    assert copy.val == (app, "fun")
    lhs_app = app
    rhs_app = net.make(APP)
    val_copy = copy
    arg_copy = net.make(COPY)
    connect((val_copy, "val"), lhs_app.val)
    connect((arg_copy, "arg"), lhs_app.arg)
    connect((lhs_app, "fun"), val_copy.lhs)
    connect((rhs_app, "fun"), val_copy.rhs)
    connect((val_copy, "lhs"), (lhs_app, "val"))
    connect((val_copy, "rhs"), (rhs_app, "val"))
    connect((arg_copy, "lhs"), (lhs_app, "arg"))
    connect((arg_copy, "rhs"), (rhs_app, "arg"))


def try_step_node(net, node):
    assert isinstance(node, Node)
    if isinstance(node, ERASE):
        val, port = node.val
        if isinstance(val, COPY):
            if port == "val":
                lhs = node
                rhs = net.make(ERASE)
                connect(lhs.val, val.lhs)
                connect(rhs.val, val.rhs)
            elif port == "lhs":
                connect(node.val, val.rhs)
            else:
                assert port == "rhs"
                connect(node.val, val.lhs)
            net.erase(val)
            return True
        elif isinstance(val, APP):
            assert node.val[1] == "val"
            val = node.val[0]
            fun = node
            arg = net.make(ERASE)
            connect((fun, "val"), val.fun)
            connect((arg, "val"), val.arg)
            net.remove(val)
            return True
        elif isinstance(val, ABS):
            if port == "val":
                var = node
                body = net.make(ERASE)
                connect((var, "val"), val.var)
                connect((body, "val"), val.body)
                net.remove(val)
                return True
    elif isinstance(node, COPY):
        if isinstance(node.val[0], APP) and node.val[1] == "fun":
            interact_copy_app(net, node, node.val[0])
        elif isinstance(node.val[0], ABS) and node.val[1] == "val":
            # Copy abs.val.
            lhs_abs = node.val[0]
            rhs_abs = net.make(ABS)
            val_copy = node
            arg_copy = net.make(COPY)
            connect((val_copy, "val"), lhs_abs.val)
            connect((arg_copy, "arg"), lhs_abs.arg)
            connect((lhs_abs, "fun"), val_copy.lhs)
            connect((rhs_abs, "fun"), val_copy.rhs)
            connect((val_copy, "lhs"), (lhs_abs, "val"))
            connect((val_copy, "rhs"), (rhs_abs, "val"))
            connect((arg_copy, "lhs"), (lhs_abs, "arg"))
            connect((arg_copy, "rhs"), (rhs_abs, "arg"))
        elif isinstance(node.val[0], COPY) and node.val[1] == "val":
            if node.id == node.val.id:
                # Cancel copies.
                connect(node.lhs, node.val.lhs)
                connect(node.rhs, node.val.rhs)
                net.remove(node)
                net.remove(node.val[0])
                return True
            else:
                # Duplicate copies.
                ax = node
                ay = net.make(COPY, node.id)
                bx = node.val
                by = net.make(COPY, node.val)
                connect(ax.val, node.lhs)
                connect(ay.val, node.rhs)
                connect(bx.val, node.val[0].lhs)
                connect(bx.val, node.val[0].rhs)
                connect(ax.lhs, bx.lhs)
                connect(ax.rhs, by.lhs)
                connect(ay.lhs, bx.rhs)
                connect(ay.rhs, by.rhs)
                TODO("create new ids")
                return True
    elif isinstance(node, APP) and isinstance(node.fun[0], ABS):
        assert node.fun[1] == "fun"
        # Beta step.
        connect(node.val, node.fun.body)
        connect(node.arg, node.fun.var)
        net.remove(node)
        net.remove(node.fun)
        return True
    elif isinstance(node, ABS):
        if isinstance(node.var[0], COPY) and node.var[1] == "val":
            # Propagate copies.
            TODO("")
    return False


def try_step_net(net):
    assert isinstance(net, Net)
    assert all(isinstance(n, Node) for n in net)
    return any(try_step_node(net, node) for node in net)


def reduce_net(net):
    assert isinstance(net, set)
    assert all(isinstance(n, Node) for n in net)
    count = 0
    while try_step_net(net):
        count += 1
    return count


# ----------------------------------------------------------------------------
# Construction


def make_root(net, node):
    assert isinstance(net, Net)
    assert isinstance(node, Node)
    assert node in net
    net.validate()
    root = net.make(ROOT)
    connect(root.root, node.val)
    net.validate()
    return root


def make_app(net, lhs, rhs):
    assert isinstance(net, Net)
    assert isinstance(lhs, Node)
    assert isinstance(rhs, Node)
    assert lhs in net
    assert rhs in net
    net.validate()
    val = APP()
    connect(val.lhs, lhs.val)
    connect(val.rhs, rhs.val)
    net.add(val)
    net.validate()


def make_abs(net, name, body):
    assert isinstance(net, Net)
    assert isinstance(name, str)
    assert isinstance(body, Node)
    net.validate()
    occurrences = []  # (node, port) pairs.
    TODO("depth first search for occurrences")
    abs_ = ABS()
    net.add(abs_)
    connect((abs_, "body"), (body, "val"))
    if not occurrences:
        erase = ERASE()
        net.add(erase)
        connect((abs_, "var"), (erase, "val"))
    else:
        var = occurrences[0]
        for rhs in occurrences[1:]:
            lhs = var
            var = COPY()
            net.add(var)
            connect((var, "lhs"), lhs)
            connect((var, "rhs"), rhs)
    net.validate()
    return abs_


# ----------------------------------------------------------------------------
# Read out

# TODO
