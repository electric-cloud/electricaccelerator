import shelve
import cPickle as pickle

class JobIndexRecord:
    def __init__(self, job):
        self.job = job

        # Other job IDs that reference this job ID
        self.ref_waiting_job_ids = []
        self.ref_dep_write_job_ids = []
        self.ref_needed_by_job_ids = []

    def getJob(self):
        return self.job

class AnnoIndex:
    BUILD_RECORD = "B"
    JOB_PREFIX = "J"
    MAKE_PROC_PREFIX = "M"

    def __init__(self, index_filename):
        self.build = None
        self.shelf = shelve.open(index_filename, protocol=2)

    def close(self):
        self.shelf.close()

    def addBuild(self, build):
        self.shelf[self.BUILD_RECORD] = build

    def addJob(self, job):
        job_key = self.JOB_PREFIX + job.getID()
        job_rec = JobIndexRecord(job)
        self.shelf[job_key] = job_rec

    def getJob(self, job_id):
        jobrec = self.shelf.get(self.JOB_PREFIX + job_id)
        if jobrec:
            job = jobrec.getJob()
            if self.build == None:
                self.build = self.shelf.get(self.BUILD_RECORD)
                if self.build == None:
                    msg = "Could not find build record"
                    raise ValueError(msg)
            job.fix_unpickled_state(self.build.make_procs)
            return job
        else:
            return None


count = 0

def create_index(build, index_filename):

    def job_cb(job, idx):
        global count
        count += 1
        if count % 100 == 0:
            print "Writing job #", count

        idx.addJob(job)

    print "Creating", index_filename
    idx = AnnoIndex(index_filename)
    build.parseJobs(job_cb, idx)

    idx.addBuild(build)

    idx.close()

