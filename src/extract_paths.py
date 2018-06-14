from collections import defaultdict
from sklearn.manifold import TSNE
from bblfsh import Node
from structures import BaseNode, ExtNode

import json
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


def extend_node(node, depth, num, leaves):
    if len(node.children) == 0:
        ext_node = ExtNode.extend_bblfsh_node(node, depth, num)
        leaves.append(ext_node)
        return ext_node, num + 1
    else:
        ext_node = ExtNode.extend_bblfsh_node(node, depth, -1)
        new_children = [None] * len(node.children)
        for i, child in enumerate(node.children):
            new_children[i], num = extend_node(child, depth + 1, num, leaves)

        ext_node.children = new_children

        return ext_node, num


def annotate_log_parents(node, parents):
    if len(parents) > 0:
        node.log_parents = [parents[i] for i in [(2 ** i)-1 for i in range(0, len(parents)) if 2 ** i < len(parents)]]
    for i, child in enumerate(node.children):
        annotate_log_parents(child, [node] + parents)


def extend_tree(root):
    ext_tree = None
    leaves = []
    if len(root.children) > 0:
        ext_tree, _ = extend_node(root, 0, 0, leaves)
        annotate_log_parents(ext_tree, [ext_tree])

    return ext_tree, leaves

def lca(u, v):
    if u.depth < v.depth:
        u, v = v, u

    # if answer is u or v, wll find it here
    for i in range(len(u.log_parents), -1, -1):
        if len(u.log_parents) > i and u.log_parents[i].depth >= v.depth:
            u = u.log_parents[i]

    if u == v:
        print("U is equal to V, returning")
        return u

    print("Length of u log_parents %s" % len(u.log_parents))
    for i in range(len(u.log_parents), -1, -1):
        if u == v:
            print("2; U is equal to V, returning")
            break
        if len(u.log_parents) > i and len(v.log_parents) > i and u.log_parents[i] != v.log_parents[i]:
            print("i: %s\n u: %s\n v: %s" % (i,u,v))
            u = u.log_parents[i]
            v = v.log_parents[i]

    print("Returning at last")
    return v.log_parents[0]


def distance(u, v, ancestor):
    dru = u.depth
    drv = v.depth
    drlca = ancestor.depth

    return dru + drv - 2*drlca


def get_path(u, v, ancestor):
    path = []
    path.append(u.token)
    while u != ancestor:
        path.append(u)
        path.append("↑")
        u = u.log_parents[0]

    path.append(ancestor)

    aux_path = []
    aux_path.append(v.token)
    while v != ancestor:
        aux_path.append(v)
        aux_path.append("↓")
        v = v.log_parents[0]

    path = path + aux_path[::-1]

    return path

def get_paths(uast_file, max_length, max_width):
    print("Processing file: {}".format(uast_file))
    uast = Node.FromString(open(uast_file, 'rb').read())

    tree, leaves = extend_tree(uast)
    json_t = tree.to_json()
    print(json_t)

    paths = []
    if len(leaves) > 1:
        for i in range(len(leaves)):
            for j in range(i+1, min(i + max_width, len(leaves))):
                u, v = leaves[i], leaves[j]
                ancestor = lca(u, v)
                d = distance(u, v, ancestor)
                if d <= max_length:
                    paths.append(get_path(u, v, ancestor))


    return paths


def print_paths(paths):
    for path in paths:
        for element in path:
            if element in ["UP", "DOWN"] or type(element) == str:
                print(element, end="")
            else:
                print(" [%s] " % (element.internal_type), end="")
        print()

def main(data, extension, output):
    files = recursive_glob(data, '*%s' % extension)

    ext_trees = [None] * len(files)
    leaves = [None] * len(files)
    for i, file in enumerate(files):
        # uast = Node.FromString(open(file, 'rb').read())

        # ext_trees[i], leaves[i] = extend_tree(uast)
        paths = get_paths(file, max_length=3, max_width=2)
        print("Paths: \n%s\n" % paths)


    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', type=str, help="Path of the data.", required=True)
    parser.add_argument('-e', '--extension', type=str, help="Extension of the files to parse",
                        required=False, default='py')
    parser.add_argument('-o', '--output', type=str, help="Path output to save the data.", required=False)

    args = parser.parse_args()
    main(args.data, args.extension, args.output)
