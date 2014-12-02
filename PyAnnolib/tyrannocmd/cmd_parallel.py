# Copyright (c) 2014 by Cisco Systems, Inc.
"""
Report on the parallelism seen in the build.
"""

import sys

from pyannolib import annolib
from tyrannolib import sequencing

def SubParser(subparsers):

    help = "Show the parallelism in a build"

    parser = subparsers.add_parser("parallel", help=help)
    parser.set_defaults(func=Run)


    parser.add_argument("anno_file")


def Run(args):

    cluster = sequencing.Cluster()
#    print "Collating Jobs", time.ctime()
    try:
        build = annolib.AnnotatedBuild(args.anno_file)
        
        # Collect all the jobs in a hash, and look for conflict jobs
        for job in build.iterJobs():
            timings = job.getTimings()
            for timing in timings:
                cluster.addTiming(timing)

    except annolib.PyAnnolibError, e:
        sys.exit(e)

#    print "Merging Overlaps", time.ctime()
    cluster.mergeOverlaps()

#    print "Calculating Histogram", time.ctime()
    concurrency = cluster.calculateHistogram()

#    print "Finished, now reporting", time.ctime()

    tot_time = 0.0
    for N_time in concurrency.values():
        tot_time += N_time

    print
    print "Parallelism Histogram for:"
    print args.anno_file
    print
    print "AGENTS       TIME PERCENT"

    discrete_Ns = concurrency.keys()
    discrete_Ns.sort()
    for N in discrete_Ns:
        N_time = concurrency[N]
        pct = 100.0 * N_time / tot_time
        print "%3d: %012s %5.1f %%" % (N, sequencing.hms(N_time), pct)

    print
    print "TOTAL TIME:", sequencing.hms(tot_time)






