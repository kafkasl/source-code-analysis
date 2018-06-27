from collections import OrderedDict
import numpy as np
import bblfsh
import json

class BaseNode(object):
    def __init__(self, roles, token, internal_type, properties, children, **kwargs):
        self.roles = tuple(roles)
        self.token = token
        self.internal_type = internal_type
        self.properties = dict(properties)
        self.strict_similarity = False
        self.children = children
        self._hash = None
        self._vector = None

    def vector(self):
        if self._vector is None:
            self._vector = self.roles_as_vector(self.roles)
        return self._vector

    @staticmethod
    def from_bblfsh_node(node):
        # token = "{} {}".format([bblfsh.role_name(i) for i in node.roles], node.token)
        return BaseNode(node.roles, node.token, node.internal_type, node.properties, node.children)

    @staticmethod
    def roles_as_vector(roles):
        vec = np.zeros(119)
        for r in roles:
            vec[r] = 1
        return vec

    def named_roles(self):
        return [bblfsh.role_name(role) for role in self.roles]

    # def __eq__(self, other):
    #     if self.strict_similarity:
    #         return (self.roles, self.token, self.internal_type, self.properties) == \
    #                (other.roles, self.token, other.internal_type, other.properties)
    #     else:
    #         return (self.roles, self.internal_type, self.properties) == \
    #                (other.roles, other.internal_type, other.properties)
    #
    # def __ne__(self, other):
    #     return not (self == other)
    #
    # # Can change this to consider different notions of equality / hashing among nodes
    # def __hash__(self):
    #     if self._hash is None:
    #         self._hash = hash(self.internal_type)
    #         # Do not consider var names etc... in the hashing
    #         if self.strict_similarity:
    #             self._hash ^= hash(self.token)
    #         for pair in self.properties.items():
    #             self._hash ^= hash(pair)
    #         for role in self.roles:
    #             self._hash ^= hash(role)
    #     return self._hash

    def __str__(self):
        text = "BaseNode(roles=" + str([bblfsh.role_name(role) for role in self.roles]) + \
               ", token=" + self.token + \
               ", internal_type=" + self.internal_type + \
               ", properties=" + str(self.properties) + ")"
        # text = "BaseNode(roles=" + self.roles + \
        return text

    def __repr__(self):
        return "[" + " ".join(["{}/{}".format(bblfsh.role_name(role), role) for role in self.roles]) + "]"
        # text = "BaseNode : [" + " ".join([bblfsh.role_name(role) for role in self.roles]) + "]\n"
        # text += " * Properties: " + " ".join([p for p in self.properties]) + "\n"
        # text += " * Internal type: " + self.internal_type + "\n"
        # return text


class ExtNode(BaseNode):
    def __init__(self, base_node, depth, numeration=-1):
        BaseNode.__init__(self, **vars(base_node))
        self.depth = depth
        self.numeration = numeration
        self.log_parents = []

    @staticmethod
    def new_node(depth, numeration=-1):
        base_node = BaseNode([], "", "", {}, [])
        return ExtNode(base_node, depth, numeration)

    @staticmethod
    def extend_bblfsh_node(node, depth, numeration=-1):
        # token = "{} {}".format([bblfsh.role_name(i) for i in node.roles], node.token)
        base_node = BaseNode(node.roles, node.token, node.internal_type, node.properties, node.children)
        return ExtNode(base_node, depth, numeration)

    def as_dict(self, fieds_to_delete=None):
        """ Represent node as a nested dict. """

        def _dict_full(node):
            # print("Type of node: %s" % type(node))
            if len(node.children) == 0:
                dct = dict(vars(node))
                del dct['children']
                # del dct['log_parents']
                for f in fieds_to_delete:
                    del dct[f]
                return dct
            else:
                dct = dict(vars(node))
                for f in fieds_to_delete:
                    del dct[f]
                # del dct['log_parents']
                dct['children'] = [_dict(n) for n in node.children]
                return dct

        def _dict(node):
            # print("Type of node: %s" % type(node))
            if len(node.children) == 0:
                return OrderedDict([("token", node.token), ("depth", node.depth), ("numeration", node.numeration)])
            else:
                children = [_dict(n) for n in node.children]
                dct = OrderedDict([("token", node.token), ("depth", node.depth), ("numeration", node.numeration),
                                   ("children", children)])
                return dct

        return _dict(self)

    def to_json(self, fields_to_delete=("_hash", "_vector", "strict_similarity",
                                        "internal_type", "roles", "properties")):
        """ Return a JSON representation of this node and all children. """
        return json.dumps(self.as_dict(fields_to_delete), indent=4, separators=(',', ': '))

    def __repr__(self):
        return json.dumps(OrderedDict([("token", self.token), ("depth", self.depth), ("numeration", self.numeration)]))

    def __str__(self):
        return json.dumps(OrderedDict([("token", self.token), ("depth", self.depth), ("numeration", self.numeration)]))
        # return "ExtNode[%s] Num: %s, Depth: %s" % (BaseNode.__repr__(self), self.numeration, self.depth)

class Rule(object):
    def __init__(self, rhs, lhs):
        self.rhs = rhs
        self.lhs = lhs
        self._hash = None

    def __eq__(self, other):
        if len(self.rhs) != len(other.rhs):
            return False
        if self.lhs != other.lhs:
            return False
        for i in range(0, len(self.rhs)):
            if self.rhs[i] != other.rhs[i]:
                return False
        return True

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(self.lhs)
            for antecedent in self.rhs:
                self._hash ^= hash(antecedent)
        return self._hash

    def __str__(self):
        text = "Rule(lhs=" + str(self.lhs) + \
               ",rhs=[".join([str(a) for a in self.rhs]) + "])"
        return text

    def __repr__(self):
        text = "Rule: " + repr(self.lhs) + "=>"
        for i, a in enumerate(self.rhs):
            text += repr(a)
            if i < len(self.rhs) - 1:
                text += "^"

        return text
