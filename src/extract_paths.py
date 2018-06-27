from collections import OrderedDict
from bblfsh import Node
from structures.extended_node import ExtNode
from pprint import pprint

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


def extend_node(node, depth, num, leaves):
    """
    Transforms a tree of nodes type(node) to ExtNode which holds information required to create paths (i.e.,
    depth, leaf number, and log_parents) and returns a list of containing all leaves.
    Log_parents are not annotated in this traversal.
    :param node: node to transform
    :param depth: current depth of traversal (0=based)
    :param num: number of leaves already numbered (i.e., # to assign to next leaf)
    :param leaves: list of seen leaves
    :return: current node as ExtNode and 'num'
    """
    if len(node.children) == 0:
        ext_node = ExtNode(node, depth, num)
        leaves.append(ext_node)
        return ext_node, num + 1
    else:
        ext_node = ExtNode(node, depth, -1)
        new_children = [None] * len(node.children)
        for i, child in enumerate(node.children):
            new_children[i], num = extend_node(child, depth + 1, num, leaves)

        ext_node.children = new_children

        return ext_node, num


def annotate_log_parents(node, parents):
    """
    Adds the log_parents attribute to each node
    :param node: current node to annotate
    :param parents: list of current node's parents until the root
    """
    if len(parents) > 0:
        node.log_parents = [parents[i] for i in [(2 ** i) - 1 for i in range(0, len(parents)) if 2 ** i < len(parents)]]
    for i, child in enumerate(node.children):
        annotate_log_parents(child, [node] + parents)


def extend_tree(root):
    """
    Transforms a tree of nodes type(node) to ExtNode which holds information required to create paths (i.e.,
    depth, leaf number, and log_parents) and returns a list of containing all leaves
    :param root: root of the tree to extend
    :return: extended tree and the list of its leaves
    """
    ext_tree = None
    leaves = []
    if len(root.children) > 0:
        ext_tree, _ = extend_node(root, 0, 0, leaves)
        annotate_log_parents(ext_tree, [ext_tree])

    return ext_tree, leaves


def lca(u, v):
    """
    Computes least common ancestor of 2 nodes (ExtNode) using log_parents and depth
    :type u: lca of the nodes
    """
    if u.depth < v.depth:
        u, v = v, u

    for i in range(len(u.log_parents), -1, -1):
        if len(u.log_parents) > i and u.log_parents[i].depth >= v.depth:
            u = u.log_parents[i]

    if u == v:
        return u

    for i in range(len(u.log_parents), -1, -1):
        if u == v:
            break
        if len(u.log_parents) > i and len(v.log_parents) > i and u.log_parents[i] != v.log_parents[i]:
            u = u.log_parents[i]
            v = v.log_parents[i]

    return v.log_parents[0]


def distance(u, v, ancestor):
    """
    Computes distance of the path from u to v using the lca node as:
        d(u,v) = d(root, u) + d(root, v) - 2 * d(root, lca)
    :param u:
    :param v:
    :param ancestor:
    :return:
    """
    dru = u.depth
    drv = v.depth
    drlca = ancestor.depth

    return dru + drv - 2 * drlca


def get_path(u, v, ancestor, split_leaves, up_symbol="UP", down_symbol="DOWN"):
    """
    Returns the path from u to v separated by up an down symbols. The path is formed by the original base nodes.
    :param u: start node
    :param v: end node
    :param ancestor: least common ancestor of u and v
    :param split_leaves: bblfsh nodes contain both the final token and an internal_type, this split it into two nodes
    :param up_symbol: symbol indicating next token is parent of the previous
    :param down_symbol: symbol indicating next token is a child of the previous
    :return:
    """
    path = []

    # TODO: bblfsh leaves contain the final symbol, split_leaves=True is coupled to base node implementation
    if split_leaves:
        path.append(u.bn.token)
        path.append(up_symbol)
    while u != ancestor:
        path.append(u.bn)
        path.append(up_symbol)
        u = u.log_parents[0]

    path.append(ancestor.bn)

    aux_path = []
    if split_leaves:
        aux_path.append(v.bn.token)
        aux_path.append(down_symbol)
    while v != ancestor:
        aux_path.append(v.bn)
        aux_path.append(down_symbol)
        v = v.log_parents[0]

    path = path + aux_path[::-1]

    return tuple(path)


# dirty hardcoding to avoid getting paths with comments as start/end
def is_noop_line(node):
    return node.bn.internal_type == 'NoopLine' or node.bn.internal_type == 'SameLineNoops'


def get_paths(uast_file, max_length, max_width, token_extractor, split_leaves=True):
    """
    Creates a list of all the paths given the max_length and max_width restrictions.
    :param uast_file: file containing a bblfsh UAST as string and binary-coded
    :param max_length:
    :param max_width:
    :param token_extractor: function to transform a node into a single string token
    :param split_leaves: get leaves token as a different node
    :return: list(list(str)) list of paths (which are list of strings)
    """
    print("Processing file: {}".format(uast_file))
    uast = Node.FromString(open(uast_file, 'rb').read())

    tree, leaves = extend_tree(uast)

    paths = []
    if len(leaves) > 1:
        for i in range(len(leaves)):
            for j in range(i + 1, min(i + max_width, len(leaves))):
                u, v = leaves[i], leaves[j]
                # TODO decide where to filter comments and decouple bblfsh
                if not is_noop_line(u) and not is_noop_line(v):
                    ancestor = lca(u, v)
                    d = distance(u, v, ancestor)
                    if d <= max_length:
                        node_path = get_path(u, v, ancestor, split_leaves=split_leaves)
                        # convert nodes to its desired representation
                        paths.append([token_extractor(p) for p in node_path])

    return paths

# aux function to print paths
def print_paths(paths, symbols_repr={"UP": "↑", "DOWN": "↓"}):
    for path in paths:
        for element in path:
            if type(element) == str and element in symbols_repr.keys():
                print("%s " % symbols_repr[element], end="")
            elif type(element) == str:
                print("%s " % element, end="")
            else:
                print("[%s] " % (element.internal_type), end="")

        print()


def get_unique_tokens(fp):
    _, paths = fp

    tokens = set()
    for path in paths:
        for token in path:
            tokens.add(token)

    return tokens


def node_to_internal_type(node):
    """
    Use the internal_type property of a node (bblfsh.Node) as its final path representation
    :param node: base_node
    :return: node's internal_type or the string itself (in case its UP/DOWN token or a leaf)
    """
    if type(node) == str:
        return node
    return node.internal_type


def node_to_roles(node):
    """
    Use the list of roles of the node to compute a hash representing the node token. Hash also the string to
    decrease collisionsultra
    :param node: base_node
    :return: node's roles or the string's hash (in case its UP/DOWN token or a leaf)
    """
    if type(node) == str:
        return hash(node)
    return hash(node.roles)


def write_to_disk(output, file_name, paths):
    # if file_name has relative paths remove them
    file_name = file_name.replace("../", "")
    file_out = os.path.join(output, file_name)

    os.makedirs(os.path.dirname(file_out), exist_ok=True)

    print("Writing id paths to %s" % file_out)

    with open(file_out, 'w') as f:
        for p in paths:
            f.write(" ".join([str(e) for e in p]) + "\n")
    f.close()


def extract_paths(data, extension, max_length, max_width):
    """
    Computes the code paths of each file and the lists of all tokens seen
    :param data: folder where the AST files are (for now bblfsh binary UASTs)
    :param extension: extension to filter by; default uast.bin as saved by 'repos_to_uast.py'
    :param max_length: max length of the code paths
    :param max_width: max number of leaves between origin and end of a given path
    :return: id_paths: tuples with file names and its list of paths , token2id: all tokens and their id
    """
    files = recursive_glob(data, '*%s' % extension)

    file_paths = [None] * len(files)
    for i, file in enumerate(files):
        p = get_paths(file, max_length=max_length, max_width=max_width, token_extractor=node_to_internal_type)
        file_paths[i] = (file, p)

    for file, paths in file_paths:
        print("\nPaths for file: %s" % file)
        print_paths(paths)

    # get unique tokens per file
    tokens_set = [None] * len(files)
    for i, fp in enumerate(file_paths):
        tokens_set[i] = get_unique_tokens(fp)

    # reduce to get global list of unique tokens
    tokens_set = sorted(set().union(*tokens_set))

    # dict is ordered, to retrieve i-th token -> list(token2id.keys())[i]
    token2id = OrderedDict([(token, i + 1) for i, token in enumerate(tokens_set)])

    print("Token2id:")
    pprint(token2id)

    id_paths = [None] * len(files)
    for i, (file_name, paths) in enumerate(file_paths):
        id_paths[i] = (file_name, [[token2id[token] for token in path] for path in paths])

    return id_paths, token2id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', type=str, help="Path of the data.", required=True)
    parser.add_argument('-e', '--extension', type=str, help="Extension of the files to parse",
                        required=False, default='uast.bin')
    parser.add_argument('-o', '--output', type=str, help="Path output to save the data.", required=False)
    parser.add_argument('-l', '--max_length', type=int, default=5, help="Max path length.", required=False)
    parser.add_argument('-w', '--max_width', type=int, default=2, help="Max path width.", required=False)

    args = parser.parse_args()

    file_paths, token2id = extract_paths(args.data, args.extension, args.max_length, args.max_width)

    for file_name, paths in file_paths:
        write_to_disk(args.output, file_name, paths)

    # we are saving also the ID although it's not necessary (word ID is just position 1-indexed)
    write_to_disk(args.output, "token2id", token2id.items())


if __name__ == '__main__':
    main()
