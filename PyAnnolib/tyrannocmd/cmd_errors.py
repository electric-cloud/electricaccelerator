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

        if job.getType() != annolib.JOB_TYPE_RULE and \
                job.getType() != annolib.JOB_TYPE_CONTINUATION:
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

def print_error_job(n, show_summary, build, job, report_type):

    make_proc = job.getMakeProcess()

    build_start_dt = build.getStartDateTime()

    if show_summary:
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

    # See if we shoudl not show the first output.
    # If it's just a repeated of the command argv, we've already
    # shown that.
    if argv and outputs:
        first_text = outputs[0].getText()
        # Ignore any whitespace at the beginning and end
        if first_text.strip() == argv.strip():
            outputs = outputs[1:]

    if outputs:
        print "-" * 30, "Output", "-" * 30
        for i, op in enumerate(outputs):
            text = op.getText()
            print text,
        print "-" * (60  + len("Output") + 2)


def print_message(n, show_summary, build, message):
    if show_summary:
        print "Cluster Manager Message #%d" % (n,)
        print

    build_start_dt = build.getStartDateTime()

    message_time = float(message.getTime())
    message_dt = build_start_dt + datetime.timedelta(seconds=message_time)

    print "%s (%s) at %s (%s)" % \
            (message.getCode(), message.getSeverity(),
                    message_dt, message.getTime())
    print message.getText()
    print

def print_header(build, show_summary, messages, error_jobs, error_makes):
    
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

    if not show_summary:
        return

    # Summary information
    print "Summary:"
    if messages:
        print "\tCluster Manager messages:", len(messages)

    if error_jobs:
        print "\tFailed commands:", len(error_jobs)

    if error_makes:
        print "\tFailed Make commands:", len(error_makes)

    print

#    print "make[0] in %s" % (props.get("CWD"),)
#    print props.get("CommandLine")
#    print

def print_footer():
    print "=" * 80


def report(build, show_summary, messages, error_jobs, error_makes):
    print_header(build, show_summary, messages, error_jobs, error_makes)


    if show_summary:
        print "-" * 80

    # Details
    for i, message in enumerate(messages):
        print_message(i+1, show_summary, build, message)
        if show_summary:
            print "-" * 80

    for i, job in enumerate(error_jobs):
        print_error_job(i+1, show_summary, build, job, TYPE_JOB)
        if show_summary:
            print "-" * 80

    for i, job in enumerate(error_makes):
        print_error_job(i+1, show_summary, build, job, TYPE_MAKE)
        if show_summary:
            print "-" * 80

    print_footer()

def Run(args):
    build = annolib.AnnotatedBuild(args.anno_file)

    # We have to parse the entire file first
    error_jobs, error_makes = find_error_jobs(build)

    messages = build.getMessages()

    if messages or error_jobs or error_makes:
        num_problems = len(messages) + len(error_jobs) + len(error_makes)
        show_summary = num_problems > 1
        report(build, show_summary, messages, error_jobs, error_makes)

