from collections import defaultdict
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans

import matplotlib.pyplot as plt
import numpy as np

import pickle
import bblfsh
import argparse
import os
import fnmatch


def plot_tsne(nodes_dict):

    """
    Compute the t-SNE dimensionality reduction values of input parameter and plot them in 2D
    :param id_word_vec: vector containing the tuples (id, word, embedding) to be plotted
    """
    nodes = [node for node, _ in nodes_dict]
    counts = [len(instances) for node, instances in nodes_dict]
    tsne = TSNE(n_components=2)
    X_tsne = tsne.fit_transform([BaseNode.roles_as_vector(n) for n in nodes])
    plt.scatter(X_tsne[:, 0], X_tsne[:, 1], s=counts)

    for i, roles in enumerate(nodes):
        plt.annotate([bblfsh.role_name(role) for role in roles], (X_tsne[i, 0], X_tsne[i, 1]))

    plt.show()


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
        self.roles = tuple(roles)
        self.token = token
        self.internal_type = internal_type
        self.properties = dict(properties)
        self.strict_similarity = False
        self._hash = None
        self._vector = None

    def vector(self):
        if self._vector is None:
            self._vector = self.roles_as_vector(self.roles)
        return self._vector

    @staticmethod
    def roles_as_vector(roles):
        vec = np.zeros(119)
        for r in roles:
            vec[r] = 1
        return vec

    def named_roles(self):
        return [bblfsh.role_name(role) for role in self.roles]

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
        return "BaseNode[" + " ".join(["{}/{}".format(bblfsh.role_name(role), role) for role in self.roles]) + "]"
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


def get_rule(node):
    if len(node.children) == 0:
        token = "{} {}".format([bblfsh.role_name(i) for i in node.roles], node.token)
        return [], BaseNode(node.roles, token, node.internal_type, node.properties)

    rules = []
    rhs = []
    tokens = "{}".format([bblfsh.role_name(i) for i in node.roles])
    for i, child in enumerate(node.children):
        c_rules, c_node = get_rule(child)
        rhs.append(c_node)

        # if i > 0:
        tokens += " "

        tokens += c_node.token
        rules.extend(c_rules)

    tokens += "\n"
    lhs = BaseNode(node.roles, tokens, node.internal_type, node.properties)
    rules.append(Rule(rhs, lhs))
    return rules, lhs


def get_rules(root):
    rules = []
    if len(root.children) > 0:
        rules, tokens = get_rule(root)
    # for i, _ in enumerate(rules):
    #     print("rule lhs:\n{}".format(rules[i].lhs.token))

    return rules

def rules_as_dict(rules):
    rules_dict = defaultdict(list)
    for rule in rules:
        rules_dict[rule].append(rule)

    return rules_dict


def get_nodes(rules):
    nodes = []
    for rule in rules:
        nodes.append(rule.lhs)
        nodes.extend(rule.rhs)

    return nodes


def nodes_as_dict(nodes):
    nodes_dict = defaultdict(list)
    for node in nodes:
        nodes_dict[node.roles].append(node)

    return nodes_dict


def process_uasts(uasts):
    rules_dict = defaultdict(int)

    rules = []
    antecedents_length = []
    for uast in uasts:
        rule = get_rules(uast)
        rules.extend(rule)


    for rule in rules_dict.keys():
        antecedents_length.append(len(rule.rhs))

    rules_dict = rules_as_dict(rules)
    nodes = get_nodes(rules)
    nodes_dict = nodes_as_dict(nodes)

    for rule in rules:
        print("\nLHS: {} => RHS: ".format(rule.lhs.token), end="")
        for child in rule.rhs:
            print("{}".format(child.token), end=",")


    print("Total number of UASTs: {}".format(len(uasts)))
    print("Total rules: {}".format(len(rules)))
    print("Total different rules: {}".format(len(rules_dict)))
    print("Total nodes: {}".format(len(nodes)))
    print("Total different nodes: {}".format(len(nodes_dict)))

    for rule in rules_dict.keys():
        antecedents_length.append(len(rule.rhs))

    print("Mean rule length: {}".format(np.mean(antecedents_length)))
    print("Std rules length: {}".format(np.std(antecedents_length)))

    rules_count = list([(k, v) for k, v in rules_dict.items()])
    nodes_count = list([(k, v) for k, v in nodes_dict.items()])

    rules_count.sort(key=lambda x: -len(x[1]))
    nodes_count.sort(key=lambda x: -len(x[1]))

    return rules_count, nodes_count


def print_statistics(rules_count, nodes_count):
    print("Top twenty rules:")
    for i in range(20):
        print("{}. {}\n".format(i, rules_count[i][0]))

    print("Top twenty nodes:")
    for i in range(20):
        print("{}. {}\n\t{}\n".format(i, [bblfsh.role_name(role_id) for role_id in nodes_count[i][0]],
                                      nodes_count[i][1][0]))

    with open('../results/rules.bin', 'w') as rules_file:
        rules_file.write("\n".join([str(r) for r in [r for r, count, in rules_count]]))


def cluster_nodes(nodes_count):
    vectors = np.matrix([BaseNode.roles_as_vector(k) for k, v in nodes_count])
    vectors.tofile('../results/vectors.bin')

    kmeans = KMeans(init='k-means++', n_clusters=3, n_init=10)
    kmeans.fit(vectors)
    results = kmeans.predict(vectors)

    plot_tsne(nodes_count)

def save_roles(output, nodes_count):
    roles_count = [(tuple([bblfsh.role_name(role_id) for role_id in n]), count) for n, count in nodes_count]
    if not os.path.exists(output):
        os.makedirs(output)
    with open('{}/{}'.format(output, 'roles_count.pickle'), 'wb') as f:
        pickle.dump(roles_count, f)


def main(data, output):

    client = bblfsh.BblfshClient("0.0.0.0:9432")
    files = recursive_glob(data, '*.py')

    uasts = []
    for file in files:
        print("Processing file: {}".format(file))
        uast = client.parse(file).uast
        if len(uast.children) > 0:
            uasts.append(uast)
    # print(uast)
    # "filter' allows you to use XPath queries to filter on result nodes:
    # print(bblfsh.filter(uast, "//Import[@roleImport and @roleDeclaration]//alias"))


    rules_count, nodes_count = process_uasts(uasts)

    # print_statistics(rules_count, nodes_count)
    #
    # cluster_nodes(nodes_count)
    #
    # save_roles(output, nodes_count)

    return

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', type=str, help="Path of the data.", required=True)
    parser.add_argument('-o', '--output', type=str, help="Path output to save the data.", required=True)

    args = parser.parse_args()
    main(args.data, args.output)

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
