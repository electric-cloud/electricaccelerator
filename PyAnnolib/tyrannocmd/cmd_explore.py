import sys
from pyannolib import annolib
import tyrannolib

def SubParser(subparsers):

    help = "Explor annoation index files"

    parser = subparsers.add_parser("explore", help=help)
    parser.set_defaults(func=Run)

    parser.add_argument("index_file")


def Run(args):
    index = tyrannolib.AnnoIndex(args.index_file)

    running = True
    while running:
        print "tyranno> ",
        sys.stdout.flush()
        cmdline = raw_input()
        
        job_id = cmdline.strip()
        job = index.getJob(job_id)
        print job.getTextReport()
