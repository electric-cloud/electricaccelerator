import sys
from pyannolib import annolib
import tyrannolib


def SubParser(subparsers):

    help = "Show data from the annoation file"

    parser = subparsers.add_parser("show", help=help)
    parser.set_defaults(func=Run)

    parser.add_argument("anno_file")
    parser.add_argument("job_or_make_ID", nargs="*")



def print_jobs(build, job_ids):


    def job_cb(job, job_ids):

        if job.getID() in job_ids:
            print job.getTextReport()
            print
            job_ids.remove(job.getID())

            # We're done; stop the search
            if len(job_ids) == 0:
                return annolib.StopParseJobs

    build.parseJobs(job_cb, job_ids)


def Run(args):
    build = annolib.AnnotatedBuild(args.anno_file)


    job_ids =  [j for j in args.job_or_make_ID if j[0] == "J"]
    make_ids = [m for m in args.job_or_make_ID if m[0] == "M"]

    if job_ids:
        print_jobs(build, job_ids)
