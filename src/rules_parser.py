from collections import defaultdict
from pprint import pprint

import numpy as np

import bblfsh
import argparse

class Node(object):
    def __init__(self, roles, token, internal_type, properties):
        self.roles = roles
        self.token = token
        self.internal_type = internal_type
        self.properties = dict(properties)
        self.strict_similarity = False
        self._hash = None

    def __eq__(self, other):
        if self.strict_similarity:
            return (self.roles, self.token, self.internal_type, self.properties) == \
               (other.roles, self.token, other.internal_type, other.properties)
        else:
            return (self.roles, self.internal_type, self.properties) == \
                (other.roles, other.internal_type, other.properties)

    def __ne__(self, other):
        return not (self == other)

    # Can change this to consider different notions of equality / hashing among nodes
    def __hash__(self):
        if self._hash is None:
            self._hash = hash(self.internal_type)
            # Do not consider var names etc... in the hashing
            if self.strict_similarity:
                self._hash ^= hash(self.token)
            for pair in self.properties.items():
                self._hash ^= hash(pair)
            for role in self.roles:
                self._hash ^= hash(role)
        return self._hash

    def __repr__(self):
        text = "Node(roles=" + str([bblfsh.role_name(role) for role in self.roles]) + \
               ", token=" + self.token + \
               ", internal_type=" + self.internal_type + \
               ", properties=" + str(self.properties) + ")"
        # text = "Node(roles=" + self.roles + \
        return text

    def __str__(self):
        return "Node[" + " ".join([bblfsh.role_name(role) for role in self.roles]) + "]"
        # text = "Node : [" + " ".join([bblfsh.role_name(role) for role in self.roles]) + "]\n"
        # text += " * Properties: " + " ".join([p for p in self.properties]) + "\n"
        # text += " * Internal type: " + self.internal_type + "\n"
        # return text


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

    def __repr__(self):
        text = "Rule(lhs=\n\t" + repr(self.lhs)  + \
            ",\n     rhs=\n\t" + "\t".join([repr(a) for a in self.rhs])+ ")\n"
        return text

    def __str__(self):
        text = "Rule: \n" + str(self.lhs)
        for i, a in enumerate(self.rhs):
            text += str(a)
            if i < len(self.rhs) - 1:
                text += ","

        return text


def get_properties(node):
    props = []
    for p in node.properties:
        props.append(p)
    return props


def get_rule(node):
    rhs = []
    for child in node.children:
        rhs.append(Node(child.roles, child.token, child.internal_type, child.properties))
    lhs = Node(node.roles, node.token, node.internal_type, node.properties)
    return Rule(rhs, lhs)


def get_rules(node):
    rules = []
    if len(node.children) > 0:
        rules.append(get_rule(node))

        for child in node.children:
            rules.append(get_rule(child))

    return rules



if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', type=str, help="Path of the data.", required=True)

    args = parser.parse_args()
    data = args.data

    client = bblfsh.BblfshClient("0.0.0.0:9432")
    uast = client.parse(data).uast
    # print(uast)
    # "filter' allows you to use XPath queries to filter on result nodes:
    # print(bblfsh.filter(uast, "//Import[@roleImport and @roleDeclaration]//alias"))
    rules = get_rules(uast)
    for rule in rules:
        # print(rule)
        # print(repr(rule))
        print(repr(rule))

    rules_dict = defaultdict(int)

    rhs_lengths = []
    uasts = [uast]
    for uast in uasts:
        rules = get_rules(uast)
        for rule in rules:
            rhs_lengths.append(len(rule.rhs))
            rules_dict[rule] += 1

    np.mean(rhs_lengths)
    np.std(rhs_lengths)
    print("Rules dictionary:")
    for k, v in rules_dict.items():
        print("{}:{}".format(str(k), v))
    # print(rules_dict)
        # filter\_[bool|string|number] must be used when using XPath functions returning
    # these types:
    # print(bblfsh.filter_bool(uast, "boolean(//*[@strtOffset or @endOffset])"))
    # print(bblfsh.filter_string(uast, "name(//*[1])"))
    # print(bblfsh.filter_number(uast, "count(//*)"))

    # You can also iterate on several tree iteration orders:
    # it = bblfsh.iterator(uast, bblfsh.TreeOrder.PRE_ORDER)
    # for node in it:
    #     print(node.internal_type)
