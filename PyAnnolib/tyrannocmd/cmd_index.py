
from pyannolib import annolib
import tyrannolib

def SubParser(subparsers):

    help = "Create index files for annotation files"

    parser = subparsers.add_parser("index", help=help)
    parser.set_defaults(func=Run)

    parser.add_argument("anno_file")
    parser.add_argument("index_file")


def Run(args):
    build = annolib.AnnotatedBuild(args.anno_file)
    tyrannolib.create_index(build, args.index_file)
