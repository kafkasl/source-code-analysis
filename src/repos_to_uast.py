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


def main(data, lang, output):
    client = bblfsh.BblfshClient("0.0.0.0:9432")
    files = recursive_glob(data, '*.%s' % lang)

    for file in files:
        print("Processing file: {}".format(file))
        uast = client.parse(file).uast
        if len(uast.children) > 0:
            out_file = "%s/%s_uast.bin" % (output, file)
            print("Writing file %s" % out_file)
            if not os.path.exists(os.path.dirname(out_file)):
                os.makedirs(os.path.dirname(out_file))
            with open(out_file, 'wb') as o:
                o.write(uast.SerializeToString())

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', type=str, help="Path of the data.", required=True)
    parser.add_argument('-e', '--extension', type=str, help="Extension of the files to parse",
                        required=False, default='py')
    parser.add_argument('-o', '--output', type=str, help="Path output to save the data.", required=True)

    args = parser.parse_args()
    main(args.data, args.extension, args.output)
