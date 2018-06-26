from collections import defaultdict
from sklearn.manifold import TSNE
from bblfsh import Node
from structures import BaseNode, ExtNode
from pprint import pprint

import numpy as np

import json
import bblfsh
import argparse
import os
import fnmatch

UP_SYMBOL = "UP"

DOWN_SYMBOL = "DOWN"


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
        node.log_parents = [parents[i] for i in [(2 ** i) - 1 for i in range(0, len(parents)) if 2 ** i < len(parents)]]
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
        # print("U is equal to V, returning")
        return u

    # print("Length of u log_parents %s" % len(u.log_parents))
    for i in range(len(u.log_parents), -1, -1):
        if u == v:
            # print("2; U is equal to V, returning")
            break
        if len(u.log_parents) > i and len(v.log_parents) > i and u.log_parents[i] != v.log_parents[i]:
            # print("i: %s\n u: %s\n v: %s" % (i, u, v))
            u = u.log_parents[i]
            v = v.log_parents[i]

    # print("Returning at last")
    return v.log_parents[0]


def distance(u, v, ancestor):
    dru = u.depth
    drv = v.depth
    drlca = ancestor.depth

    return dru + drv - 2 * drlca


def get_path(u, v, ancestor, include_leaves):
    path = []

    if include_leaves:
        path.append(u.token)
        path.append(UP_SYMBOL)
    while u != ancestor:
        path.append(u)
        path.append(UP_SYMBOL)
        u = u.log_parents[0]

    path.append(ancestor)

    aux_path = []
    if include_leaves:
        aux_path.append(v.token)
        aux_path.append(DOWN_SYMBOL)
    while v != ancestor:
        aux_path.append(v)
        aux_path.append(DOWN_SYMBOL)
        v = v.log_parents[0]

    path = path + aux_path[::-1]

    return tuple(path)


def get_paths(uast_file, max_length, max_width, include_leaves=True):
    print("Processing file: {}".format(uast_file))
    uast = Node.FromString(open(uast_file, 'rb').read())

    tree, leaves = extend_tree(uast)
    json_t = tree.to_json()
    print(json_t)

    paths = []
    if len(leaves) > 1:
        for i in range(len(leaves)):
            for j in range(i + 1, min(i + max_width, len(leaves))):
                u, v = leaves[i], leaves[j]
                ancestor = lca(u, v)
                d = distance(u, v, ancestor)
                if d <= max_length:
                    paths.append(get_path(u, v, ancestor, include_leaves))

    return paths


def print_paths(file_paths):
    file, paths = file_paths
    print("Paths for file: %s\n" % file)
    for path in paths:
        for element in path:
            if element == UP_SYMBOL:
                print("↑ ", end="")
            elif element == DOWN_SYMBOL:
                print("↓ ", end="")
            elif type(element) == str:
                print("%s " % element, end="")
            else:
                print("[%s] " % (element.internal_type), end="")
        print()


def identity(element):
    return element


def internal_types(element):
    try:
        return element.internal_type
    except:
        return element


def get_unique_tokens(fp, token_extractor=internal_types):
    _, paths = fp

    tokens = set()
    for path in paths:
        for token in path:
            tokens.add(token_extractor(token))

    return tokens


def to_sparse_matrix(fp, row_size, token2id, token_extractor=internal_types):
    file, paths = fp

    from scipy.sparse import csr_matrix

    # Prepare the rows
    data = np.empty((len(paths), row_size,))
    data[:] = 0
    for i, path in enumerate(paths):
        for j, elem in enumerate(path):
            data[i][j] = token2id[token_extractor(elem)]

    # mask = numpy.random.randint(0, 5, data.shape)
    # data *= (mask >= 4)
    # del mask
    m = csr_matrix(data, dtype=np.int32)
    # del data

    print("Data:\n%s" % data)
    print("Matrix:\n%s" % m)
    return (file, m)


def weighted_min_hash(file_matrix):
    import libMHCUDA

    file, m = file_matrix
    # We've got 80% sparse matrix 6400 x 130
    # Initialize the hasher aka "generator" with 128 hash samples for every row
    gen = libMHCUDA.minhash_cuda_init(m.shape[-1], 128, seed=1, verbosity=1)

    # Calculate the hashes. Can be executed several times with different number of rows
    hashes = libMHCUDA.minhash_cuda_calc(gen, m)

    # Free the resources
    libMHCUDA.minhash_cuda_fini(gen)

    return file, hashes


def pipeline(data, extension, output, max_length, max_width):
    files = recursive_glob(data, '*%s' % extension)

    file_paths = [None] * len(files)
    for i, file in enumerate(files):
        file_paths[i] = (file, get_paths(file, max_length=max_length, max_width=max_width))

    for fp in file_paths:
        print_paths(fp)

    # get unique tokens per file
    different_tokens = [None] * len(files)
    for i, fp in enumerate(file_paths):
        different_tokens[i] = get_unique_tokens(fp)

    # reduce to get global list of tokens
    token_list = frozenset().union(*different_tokens)

    token2id = {token: i+1 for i, token in enumerate(token_list)}

    print("Token2id:")
    pprint(token2id)
    sparse_matrices = [None] * len(files)
    # build the sparse matrices
    for i, fp in enumerate(file_paths):
        sparse_matrices[i] = to_sparse_matrix(fp, row_size=(2*(2+max_length))+1, token2id=token2id)

    wmh = [None] * len(files)
    for i, fm in enumerate(file_paths):
        wmh[i] = weighted_min_hash(fm)

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', type=str, help="Path of the data.", required=True)
    parser.add_argument('-e', '--extension', type=str, help="Extension of the files to parse",
                        required=False, default='py')
    parser.add_argument('-o', '--output', type=str, help="Path output to save the data.", required=False)
    parser.add_argument('-l', '--max_length', type=int, default=5, help="Max path length.", required=False)
    parser.add_argument('-w', '--max_width', type=int, default=2, help="Max path width.", required=False)

    args = parser.parse_args()
    pipeline(args.data, args.extension, args.output, args.max_length, args.max_width)
