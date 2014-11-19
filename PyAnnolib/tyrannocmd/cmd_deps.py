# Copyright (c) 2014 by Cisco Systems, Inc.
"""
Show the dependencies for the build.
"""

# This script uses two concurrent processes to speed up the
# analyzis of the annotation file. The parsing of the annotation XML
# must be done serially, and the it is only when each datum from
# that analysis is ready that it can be reproted.
# However, we split the two naturally-serial pieces of
# work into two separate processes that can operate at their own pace.
# There is a queue between them, which the annotation parser feeds.
# In this way, the annotation parse can proceed as fast as possible,
# queuing up its results into small Python objects, and while
# the reportor is working, the parser is still proceeding ahead,
# parsing XML (which can be slow).
#
#   +--------------+                 +--------------+      
#   |              |   +---------+   |              |
#   |              |   |         |   |              |
#   |  Annotation  |   |         |   |  Dependency  |
#   |    Parser    |-->|  Queue  |-->|   Reporter   |
#   |              |   |         |   |              |
#   |              |   +---------+   |              |
#   +--------------+                 +--------------+      
#
# The Dependency Reporter runs in the main process. The Annotation Parser
# runs in a child process, and terminates once the parse is complete.

import sys
import multiprocessing

from pyannolib import annolib

def SubParser(subparsers):

    help = "Produce a report of dependencies"

    parser = subparsers.add_parser("deps", help=help)
    parser.set_defaults(func=Run)


    parser.add_argument("--makefile", metavar="FILE",
            help="Write in makefile format to FILE")

    parser.add_argument("anno_file")
    parser.add_argument("root_labels", nargs="*")



# Indices for our operation typles
OP_TYPE = 0
OP_FILE = 1

# The annotation-file file-operation categories
# We leave out a few that don't appear to be related to
# what we waant, like 'blindcrete' and 'submake'
READ_OPS = [ "read", "lookup" ]
WRITE_OPS = [
        "read",
        "create",
        "modify",
        "unlink",
        "rename",
        "link",
        "modifyAttrs",
        "append",
]


#================================================= start of child process
def read_annofile(build, roots_hash, anno_queue):
    """Read an annotation file and feed the file operations
    into the queue. The records put into the queue are tuples of

    (job_id, [read_ops], [write_ops])

    Each "ops" list is a list of tuples of form:
    (op_type, relative_filename).

    When the parse is finished, a None is written to the queue,
    and the function finishes, causing the child process to
    terminate."""

    def op_tuple(op):
        """Given an Operation object from PyAnnolib,
        return a tuple of (op, relpath), where relpath
        is relative to one of the emake roots."""
        op_type = op.getType()
        abspath = op.getFile()
        for root_path, label in roots_hash.items():
            if abspath[:len(root_path)] == root_path:
                if label:
                    relpath = "${%s}/%s" % (label, abspath[len(root_path)+1:])
                else:
                    relpath = abspath[len(root_path)+1:]
                break
        else:
            # This will never happen, as all paths
            # must be under an emake root, or they would
            # not appear in the annotation file. But stil...
            relpath = abspath

        return (op_type, relpath)

    def find_rule_jobs(job, _):
        """Return the interesting rule jobs."""

        # We only want jobs of certain types
        job_type = job.getType()
        if job_type != annolib.JOB_TYPE_RULE:
            return

        # And only successful jobs
        if job.getRetval() != 0:
            return

        make_proc = job.getMakeProcess()
#        job_cwd = make_proc.getCWD()
#        len_job_cwd = len(job_cwd)

        # Divide all the file operations into 2 groups,
        # one for reading, and one for writing
        # Items are (op, relpath) tuples
        read_ops = []
        write_ops = []

        for op in job.getOperations():
            op_type = op.getType()

            if op_type in READ_OPS:
                read_ops.append(op_tuple(op))

            elif op_type in WRITE_OPS:
                write_ops.append(op_tuple(op))

            else:
                # Ignore all other op types
                pass

        # Proceed only if we have both read and write operations
        if (not read_ops) or (not write_ops):
            return

        anno_queue.put((job.getID(), read_ops, write_ops))

    build.parseJobs(find_rule_jobs)

    # Indicate it's the end of the stream
    anno_queue.put(None)

    # We don't have to do this, but let's
    anno_queue.close()
#================================================= end of child process

def find_emake_roots(build, root_labels):
    """Return the list of emake roots (absolute paths) used
    in this build."""

    # Sanity check; root_labels should be 'name=value'
    for root_label in root_labels:
        n = root_label.count("=")
        if n != 1:
            msg = "%s should be of format 'label=path'" % (root_label,)
            sys.exit(msg)

    # Create a hash from the root labels on the comand-line
    # Key = path, Value = label (from CLI)
    label_map = {}
    for root_label in root_labels:
        name, path = root_label.split("=")
        label_map[path] = name

    # Find the roots from the anno file
    roots_string = build.getProperty("EmakeRoots")
    if not roots_string:
        sys.exit("No emake roots found.")

    root_paths = roots_string.split(":")

    # Create the roots hash to be used during analysis
    # Key = path, Value = label (or None)
    roots_hash = { root_path : label_map.get(root_path) 
            for root_path in root_paths }

    return roots_hash


def analyze_job_records(build, roots_hash, reporter):
    """Spawns the child process to parse the annotation file,
    and from the records returned from the parser, constructs
    a DAG. Returns the DAG object and the list of job nodes."""

    # Create a queue so the child process, which reads
    # the annotation file, can send information back to us.
    anno_queue = multiprocessing.Queue()

    # Analyze the annotation file in another process
    p = multiprocessing.Process(target=read_annofile,
            args=(build, roots_hash, anno_queue))
    p.start()

    # Get the first item (blocking until there is one to retreive)
    REC_JOB_ID = 0
    REC_READ_OPS = 1
    REC_WRITE_OPS = 2
    record = anno_queue.get()
    while record:
        print >> sys.stderr, "%s, qsize=%d, read=%d, write=%d" % \
                (record[REC_JOB_ID], anno_queue.qsize(),
                    len(record[REC_READ_OPS]), len(record[REC_WRITE_OPS]))

        reporter.job_record(record[REC_JOB_ID],
                record[REC_READ_OPS], record[REC_WRITE_OPS])
        record = anno_queue.get()
    
    p.join()


class MakefileReporter:

    def __init__(self, args, roots_hash):
        self.filename = args.makefile
        self.roots_hash = roots_hash

    def open(self):
        try:
            self.fh = open(self.filename, "w")
        except IOError as e:
            sys.exit(e)

        i = 1
        for root_path, label in self.roots_hash.items():
            if label:
                print >> self.fh, "# %d. %s = %s" % (i, label, root_path)
            else:
                print >> self.fh, "# %d. (No name) %s" % (i, root_path)
            i += 1

        print >> self.fh

    def job_record(self, job_id, read_ops, write_ops):
        w_files = [op[OP_FILE] for op in write_ops]
        r_files = [op[OP_FILE] for op in read_ops]

        print >> self.fh, "# %s" % (job_id,)
        print >> self.fh, " ".join(w_files), ":", " ".join(r_files)
        print >> self.fh

    def close(self):
        try:
            self.fh.close()
        except IOError:
            pass


def Run(args):
    build = annolib.AnnotatedBuild(args.anno_file)

    # Find the emake roots
    roots_hash = find_emake_roots(build, args.root_labels)

    if args.makefile:
        reporter = MakefileReporter(args, roots_hash)
    else:
        sys.exit("Need --makefile")

    # Gather the job records and print
    reporter.open()
    analyze_job_records(build, roots_hash, reporter)
    reporter.close()
