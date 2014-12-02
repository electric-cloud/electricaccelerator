# Copyright (c) 2014 by Cisco Systems, Inc.

from pyannolib import annolib

def SubParser(subparsers):

    help = "Show data from the annotation file"

    parser = subparsers.add_parser("show", help=help)
    parser.set_defaults(func=Run)

    parser.add_argument("--metric", metavar="NAME", action="append",
            help="Show metric value (can be given more than once)")

    parser.add_argument("anno_file")

    parser.add_argument("job_or_make_ID", nargs="*")



def print_jobs(build, job_ids):

    for job in build.iterJobs():
        if job.getID() in job_ids:
            print job.getTextReport()
            print
            job_ids.remove(job.getID())

            # We're done; stop the search
            if len(job_ids) == 0:
                break

def Run(args):
    build = annolib.AnnotatedBuild(args.anno_file)


    job_ids =  [j for j in args.job_or_make_ID if j[0] == "J"]
    #make_ids = [m for m in args.job_or_make_ID if m[0] == "M"]

    if job_ids:
        print_jobs(build, job_ids)

    if args.metric:
        for metric_name in args.metric:
            print metric_name, build.getMetric(metric_name)

