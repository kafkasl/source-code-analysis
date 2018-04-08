from collections import defaultdict
from pprint import pprint

import numpy as np

import bblfsh
import argparse

import os
import fnmatch


def recursive_glob(rootdir='.', pattern='*'):
    """Search recursively for files matching a specified pattern.
    Adapted from http://stackoverflow.com/questions/2186525/use-a-glob-to-find-files-recursively-in-python
    """
    matches = []
    for root, dirnames, filenames in os.walk(rootdir):
        for filename in fnmatch.filter(filenames, pattern):
            matches.append(os.path.join(root, filename))

    return matches


class BaseNode(object):
    def __init__(self, roles, token, internal_type, properties):
        self.roles = roles
        self.token = token
        self.internal_type = internal_type
        self.properties = dict(properties)
        self.strict_similarity = False
        self._hash = None
        self.vector = self.__to_vector__(roles)

    def __to_vector__(self, roles):
        vec = np.zeros(119)
        for r in roles:
            vec[r] = 1
        return vec

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

    def __str__(self):
        text = "BaseNode(roles=" + str([bblfsh.role_name(role) for role in self.roles]) + \
               ", token=" + self.token + \
               ", internal_type=" + self.internal_type + \
               ", properties=" + str(self.properties) + ")"
        # text = "BaseNode(roles=" + self.roles + \
        return text

    def __repr__(self):
        return "BaseNode[" + " ".join([bblfsh.role_name(role) for role in self.roles]) + "]"
        # text = "BaseNode : [" + " ".join([bblfsh.role_name(role) for role in self.roles]) + "]\n"
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

    def __str__(self):
        text = "Rule(\n  lhs=\n    " + repr(self.lhs)  + \
            ",\n  rhs=\n    " + "\n    ".join([repr(a) for a in self.rhs]) + "\n)"
        return text

    def __repr__(self):
        text = "Rule: " + repr(self.lhs) + "=>"
        for i, a in enumerate(self.rhs):
            text += repr(a)
            if i < len(self.rhs) - 1:
                text += "^"

        return text

def get_rule(node):
    rhs = []
    for child in node.children:
        rhs.append(BaseNode(child.roles, child.token, child.internal_type, child.properties))
    lhs = BaseNode(node.roles, node.token, node.internal_type, node.properties)
    return Rule(rhs, lhs)

def get_rules(root):
    rules = []
    if len(root.children) > 0:

        for node in root.children:
            rule = get_rule(node)
            rules.append(rule)

    return rules

def rules_as_dict(rules):
    rules_dict = defaultdict(int)
    for rule in rules:
        rules_dict[rule] += 1

    return rules_dict


def get_nodes(rules):
    nodes = []
    for rule in rules:
        nodes.append(rule.lhs)
        nodes.extend(rule.rhs)

    return nodes


def nodes_as_dict(nodes):
    nodes_dict = defaultdict(int)
    for node in nodes:
        nodes_dict[node] += 1

    return nodes_dict


def process_uasts(uasts):
    rules_dict = defaultdict(int)

    rules = []
    antecedents_length = []
    for uast in uasts:
        rules.extend(get_rules(uast))

    for rule in rules_dict.keys():
        antecedents_length.append(len(rule.rhs))

    rules_dict = rules_as_dict(rules)
    nodes = get_nodes(rules)
    nodes_dict = nodes_as_dict(nodes)

    print("Total number of UASTs: {}".format(len(uasts)))
    print("Total rules: {}".format(len(rules)))
    print("Total different rules: {}".format(len(rules_dict)))
    print("Total nodes: {}".format(len(nodes)))
    print("Total different nodes: {}".format(len(nodes_dict)))

    for rule in rules_dict.keys():
        antecedents_length.append(len(rule.rhs))

    print("Mean rule lenght: {}".format(np.mean(antecedents_length)))
    print("Std rules length: {}".format(np.std(antecedents_length)))

    rules_count = list([(k, v) for k, v in rules_dict.items()])
    nodes_count = list([(k, v) for k, v in nodes_dict.items()])

    rules_count.sort(key=lambda x: -x[1])
    nodes_count.sort(key=lambda x: -x[1])

    print("Top five rules:")
    for i in range(5):
        print("{}. {}".format(i, rules_count[i]))

    print("Top five nodes:")
    for i in range(5):
        print("{}. {}".format(i, nodes_count[i]))

    vectors = np.matrix([k.vector for k, v in nodes_count])

    with open('../results/rules.bin', 'w') as rules_file:
        rules_file.write("\n".join(rules))

    vectors.tofile('../results/vectors.bin')



if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', type=str, help="Path of the data.", required=True)

    args = parser.parse_args()
    data = args.data

    client = bblfsh.BblfshClient("0.0.0.0:9432")
    files = recursive_glob('/home/hydra/projects', '*.py')

    uasts = []
    for file in files:
        uast = client.parse(file).uast
        uasts.append(uast)
    # print(uast)
    # "filter' allows you to use XPath queries to filter on result nodes:
    # print(bblfsh.filter(uast, "//Import[@roleImport and @roleDeclaration]//alias"))

    rules = []

    antecedents_length = []

    process_uasts(uasts)
    # print("Printing rules dictionary:")
    # for k, v in rules_dict.items():
    #     print("{}:{}\n".format(str(k), v))


    # print("Representing rules dictionary:")
    # for k, v in rules_dict.items():
    #     print("{}:{}\n".format(repr(k), v))
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
