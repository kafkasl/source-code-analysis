from sourced.engine import Engine
from pyspark.sql import SparkSession
from pyspark import StorageLevel

from rules_parser import *
from bblfsh import Node

import argparse

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', type=str, help="Path of the data.", required=True)
    parser.add_argument('-o', '--output', type=str, help="Path output to save the data.", required=False)

    args = parser.parse_args()
    data = args.data


    spark = SparkSession.builder \
        .master("local[*]").appName("Examples") \
        .getOrCreate()

    #engine = Engine(spark, "/home/hydra/projects/source_d/repositories/siva.srd/latest/*", "siva")
    # engine = Engine(spark, "/home/hydra/projects/source_d/repositories/siva.srd/latest/*", "siva")
    engine = Engine(spark, "/home/hydra/projects/source_d/data/selected_repositories/siva/latest/*", "siva")
    engine = Engine(spark, args.data, "siva")
    print("%d repositories successfully loaded" % (engine.repositories.count()/2))

    binary_uasts = engine.repositories.references.head_ref.commits.tree_entries.blobs \
        .classify_languages().where('lang = "Python"') \
        .extract_uasts().select('path', 'uast').rdd.filter(lambda r: len(r['uast']) > 0).collect()

    uasts = []

    for b_uast in binary_uasts:
        uasts.append(Node.FromString(b_uast["uast"][0]))

    del binary_uasts


    rules_count, nodes_count = process_uasts(uasts)

    print_statistics(rules_count, nodes_count)

    cluster_nodes(nodes_count)

    # save_roles(args.output, nodes_count)

if __name__ == '__main__':

    main()



# uasts = engine.repositories.references.head_ref.commits.tree_entries.blobs\
#     .classify_languages().where('lang = "Python"')\
#     .extract_uasts().select('repository_id')
#
# uasts = engine.repositories.references.head_ref.commits.tree_entries.blobs\
#     .classify_languages().where('lang = "Python"')\
#     .extract_uasts().query_uast('//*[@roleIdentifier]')\
#     .extract_tokens('result', 'tokens').select('repository_id')
#
# uast = Node.FromString(uasts.first()["uast"][0])
#
#
#
#
#
#
# engine.repositories.references.head_ref.commits.tree_entries.blobs\
#     .classify_languages().where('lang = "Python"')\
#     .extract_uasts().query_uast('//*[@roleIdentifier]')\
#     .extract_tokens('result', 'tokens').select('blob_id', 'path', 'lang', 'uast', 'tokens').show()
#
#
# engine.repositories.references.head_ref.commits.tree_entries.blobs\
#     .classify_languages().where('lang = "Python"')\
#     .extract_uasts().query_uast('//*[@roleIdentifier]')\
#     .extract_tokens('result', 'tokens').select('uast').show()
#
#
# engine.parse_uast_node(uasts[0]["uast"])
#
#
# engine.repositories.printSchema()
# engine.repositories.show()
#
# engine.repositories\
#     .references.filter("is_remote = true")\
#     .select("repository_id")\
#     .distinct()\
#     .show(10, False)
#
# # head_blobs = engine.repositories.filter("is_fork = false")\
# #     .references.filter("is_remote = true")\
# #     .head_ref.commits.tree_entries.blobs\
# #     .printSchema()
#
#
# head_blobs = engine.repositories.filter("is_fork = false")\
#     .references.filter("is_remote = true")\
#     .head_ref.commits\
#     .tree_entries.blobs\
#     .classify_languages()\
#     .filter("is_binary = false")\
#     .filter("lang = 'Python'")\
#     .extract_uasts()\
#     .limit(50)\
#     .cache()
