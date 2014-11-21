import sys
from pyannolib import annolib
import tyrannolib
import datetime


TYPE_JOB = 0
TYPE_MAKE = 1

def SubParser(subparsers):

    help = "Produce a nice error report"

    parser = subparsers.add_parser("errors", help=help)
    parser.set_defaults(func=Run)

    parser.add_argument("anno_file")

def find_error_jobs(build):
    """Returns all the Jobs that were not successful."""

    job_errors = []
    make_errors = []

    def cb(job, _):

        if job.getType() != annolib.JOB_TYPE_RULE:
            return
        if job.getRetval() == job.SUCCESS:
            return

        if job.getOutputs():
            make_errors.append(job)
        else:
            job_errors.append(job)

    build.parseJobs(cb)
    return job_errors, make_errors



def report_make_chain(chain):
    for make_proc in chain:
        print "%s make[%s] in %s" % (make_proc.getID(),
                make_proc.getLevel(), make_proc.getCWD())
        print make_proc.getCmd()
        print

def print_error_job(n, build, job, report_type):

    make_proc = job.getMakeProcess()

    build_start_dt = build.getStartDateTime()

    if report_type == TYPE_JOB:
        print "Failed Command #%d: %s" % (n, job.getName())
    else:
        print "Failed Make #%d" % (n,)
    print

#    print "(%s)" % (job.getName())
    print
    print "Job ID: %s , Exit Value %s" % (job.getID(), job.getRetval())
    print "CWD: %s" % (make_proc.getCWD(),)

    for timing in job.getTimings():
        job_start = float(timing.getInvoked())
        job_end = float(timing.getCompleted())
        job_start_dt = build_start_dt + datetime.timedelta(seconds=job_start)
        job_end_dt = build_start_dt + datetime.timedelta(seconds=job_end)

        print "Node: %s  Start: %s (%s)" % (timing.getNode(), job_start_dt,
                timing.getInvoked())
        print "      %s  End:   %s (%s)" % (" " * len(timing.getNode()),
                job_end_dt, timing.getCompleted())
    print

    for cmd in job.getCommands():
        print "Command:\n"
        argv = cmd.getArgv()
        print argv
        print
        print_outputs(argv, cmd.getOutputs())
        print
   
    make_job_outputs = job.getOutputs()
    if make_job_outputs:
        print "Make Process Hierarchy:"
        print

        make_chain = build.getMakePath(job)
        report_make_chain(make_chain)

        print_outputs(None, make_job_outputs)

def print_outputs(argv, outputs):
    print "-" * 30, "Output", "-" * 30
    for i, op in enumerate(outputs):
        text = op.getText()
        if i == 0 and argv != None and text == argv + "\n":
            # If Make prints the command (no "@" at the beginning
            # of the line in the action), it will look just like argv,
            # so let's avoid printing it again here.
            continue
        elif i == 0 and text == "\n":
            continue
        else:
            print text,
    print "-" * (60  + len("Output") + 2)

def print_needed_by(all_jobs, job):
    print "%s %s (%s:%s) needed by" % (job.getID(), job.getName(),
            job.getFile(), job.getLine()),
    next_job_id = job.getNeededBy()
    next_job = all_jobs.get(next_job_id)
    if next_job:
        print ":"
        print_needed_by(all_jobs, next_job)
    else:
        print "top-level Make"
        print

def print_waiting_jobs(all_jobs, job, seen=None, indent=0):
    if seen == None:
        seen = {}

    if not job.getID() in seen:
#        print job.getID(), "waiting on", job.getWaitingJobs()
        spaces = "  " * indent

        if job.getName():
            print "%s%s %s (%s:%s)" % (spaces, job.getID(),
                    job.getName(), job.getFile(),
                    job.getLine())
        else:
            pass
#            print "%s" % (job.getID(),)
#            for op in job.getOutputs():
#                print op.getText(),

        seen[job.getID()] = True
        print

#    print "WAITING:", job.getWaitingJobs()
    for waiting_job_id in job.getWaitingJobs():
        if waiting_job_id in seen:
            continue
        waiting_job = all_jobs.get(waiting_job_id)
        if waiting_job:
            print_waiting_jobs(all_jobs, waiting_job, seen, indent+1)

def print_message(n, message):
    print "Cluster Manager Message #%d" % (n,)
    print
    print "%s (%s) at %s seconds" % \
            (message.getCode(), message.getSeverity(),
                    message.getTime())
    print message.getText()
    print
    print "-" * 80

def print_header(build, messages, error_jobs, error_makes):
    
    # Newer versions of emake have this property
    hostname = build.getProperty("UnixNodename")

    # Older versions do not, so let's look for $HOSTNAME
    if not hostname:
        hostname = build.getVar("HOSTNAME")

    print "=" * 80
    print
    print "Build ID: %s on Host %s, Cluster Manager: %s" % \
            (build.getBuildID(), hostname, build.getCM())
    print "Start Time: %s" % (build.getStart(),)
    print

    # Summary information
    print "Summary:"
    if messages:
        print "\tCluster Manager messages:", len(messages)

    if error_jobs:
        print "\tFailed commands:", len(error_jobs)

    if error_makes:
        print "\tFailed Make commands:", len(error_makes)

    print
    print "-" * 80

#    print "make[0] in %s" % (props.get("CWD"),)
#    print props.get("CommandLine")
#    print

def print_footer():
    print "=" * 80


def report(build, messages, error_jobs, error_makes):
    print_header(build, messages, error_jobs, error_makes)

    # Details
    for i, message in enumerate(messages):
        print_message(i+1, message)

    for i, job in enumerate(error_jobs):
        print_error_job(i+1, build, job, TYPE_JOB)

    for i, job in enumerate(error_makes):
        print_error_job(i+1, build, job, TYPE_MAKE)

    print_footer()

def Run(args):
    build = annolib.AnnotatedBuild(args.anno_file)

    # We have to parse the entire file first
    error_jobs, error_makes = find_error_jobs(build)

    messages = build.getMessages()

    if messages or error_jobs or error_makes:
        report(build, messages, error_jobs, error_makes)

#    if error_jobs:

#        for job in error_jobs:
#            print_error_job(jobs, build, job)
#        print_footer()


