import sys
from pyannolib import annolib
import tyrannolib
import datetime

def SubParser(subparsers):

    help = "Produce a nice error report"

    parser = subparsers.add_parser("errors", help=help)
    parser.set_defaults(func=Run)

    parser.add_argument("anno_file")


def find_error_jobs(build):
    error_jobs = []
    looking_for = set()
    jobs = {}

    def cb(job,_errors):
        job_id = job.getID()
        if job_id in looking_for:
            jobs[job_id] = job
            looking_for.remove(job_id)
            looking_for.add(job.getNeededBy())
            for waiting_job_id in job.getWaitingJobs():
                looking_for.add(waiting_job_id)

        if job.getType() != annolib.JOB_TYPE_RULE:
            return
        if job.getRetval() == job.SUCCESS:
            return

        error_jobs.append(job)
        looking_for.add(job.getNeededBy())
        for waiting_job_id in job.getWaitingJobs():
            looking_for.add(waiting_job_id)

    build.parseJobs(cb)
    return error_jobs, jobs


def print_header(build):
    props = build.getProperties()
    print "Build ID: %s on Host %s, Cluster Manager: %s" % \
            (build.getBuildID(), props.get("UnixNodename"),
            build.getCM())
    print "Start Time: %s" % (build.getStart(),)
    print
#    print "make[0] in %s" % (props.get("CWD"),)
#    print props.get("CommandLine")
#    print

def print_footer():
    print "=" * 80

def report_make_chain(chain):
    for make_proc in chain:
        print "%s make[%s] in %s" % (make_proc.getID(),
                make_proc.getLevel(), make_proc.getCWD())
        print make_proc.getCmd()
        print

def print_error_job(all_jobs, build, job):

    print "=" * 80

    make_proc = job.getMakeProcess()

    build_start_dt = build.getStartDateTime()

    print "(%s)" % (job.getName())
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

    print "Target chain:"
    print_needed_by(all_jobs, job)


    for cmd in job.getCommands():
        print "Command:"
        argv = cmd.getArgv()
        print argv
        print
        print "---Output-----------------------------------------------------"
        for i, op in enumerate(cmd.getOutputs()):
            text = op.getText()
            if i == 0 and text == argv + "\n":
                # If Make prints the command (no "@" at the beginning
                # of the line in the action), it will look just like argv,
                # so let's avoid printing it again here.
                continue
            elif i == 0 and text == "\n":
                continue
            else:
                print text,

        print "--------------------------------------------------------------"
        print
   
    make_job_outputs = job.getOutputs()
    if make_job_outputs:
        print "Error from makefile parse job:"
        for op in make_job_outputs:
            print op.getTextReport()

    #print "Waiting jobs:"
    #print_waiting_jobs(all_jobs, job)

    #print "Make Process Hierarchy:"
    #print

    #make_chain = build.getMakePath(job)
    #report_make_chain(make_chain)

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


def Run(args):
    build = annolib.AnnotatedBuild(args.anno_file)

    error_jobs, jobs = find_error_jobs(build)
    if error_jobs:

        print_header(build)
        for job in error_jobs:
            print_error_job(jobs, build, job)
        print_footer()


