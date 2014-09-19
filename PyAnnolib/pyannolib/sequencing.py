"""
Code for analyzing the sequencing of jobs, as they
are ordered in the agent nodes in the cluster.
"""

from pyannolib import annolib

# Indices into the fragment tuple
INVOKED = 1
COMPLETED = 0

# We need to round the timings down to fewer decimal points.
# This value seems to work well enough
NUM_DECIMAL_PLACES = 4


class SequencingError(Exception):
    pass

class Agent:
    """Represents one agent, which can only run one job at a time.
    Thus, an agent is also a single timeline along which jobs run serially.
    """

    def __init__(self):
        # A time fragment is a tuple of (start, end), or in
        # Electric Accelerator parlance, (invoked, completed)
        #
        # This is sorted in descending order by end time.
        self.fragments = []

        # The start of our first fragment, and end of our last fragment,
        # for error checking.
        self.absolute_invoked = None
        self.absolute_completed = None

    def pop(self):
        if len(self.fragments) >= 1:
            frag = self.fragments[0]
            del self.fragments[0]
            return frag
        else:
            return None

    def addTiming(self, timing):
        """Add a new timing object's time fragment to our list."""
        invoked = float(timing.getInvoked())
        completed = float(timing.getCompleted())
        self.addTimingTuple(invoked, completed)

    def addTimingTuple(self, invoked, completed):
        """Add a new fragment to our list."""

        # Basic sanity test
        if completed < invoked:
            msg = "Invoked time is after Completed time. No Time Travel!"
            raise SequencingError(msg)

        # No reason to order it this way, except that we
        # keep these fragements in reversed-sorted order. So if we
        # print out the whole list, it visibly makes more sense to 
        # show the completed time first, and the invoked time second.
        new_frag = (round(completed, NUM_DECIMAL_PLACES),
                round(invoked, NUM_DECIMAL_PLACES))

        # Are we empty?
        if len(self.fragments) == 0:
            self.fragments.append(new_frag)

        # Does the fragment come after the last fragment completed??
        elif invoked > self.fragments[0][COMPLETED]:
            self.fragments.insert(0, new_frag)

        # No? Does the fragement start inside the last fragment?
        elif invoked > self.fragments[0][INVOKED]:
            self.fragments.insert(0, new_frag)

        # Does the fragment come before all other fragments?
        elif invoked < self.fragments[-1][INVOKED]:
            self.fragments.append(new_frag)

        # Find the gap where we can insert the fragment. Because some
        # jobs can overlap, there may not be a gap where we can place it.
        # Be make our best effort; we will deal with merging the fragments
        # later. 
        else:
            # Find the fragments surrounding this fragment's start time
            prev_frag = None
            for i, next_frag in enumerate(self.fragments):
                # Skip the first fragment; we already checked that boundary
                if i == 0:
                    prev_frag = next_frag
                    continue

                prev_completed = prev_frag[COMPLETED]
                prev_invoked = prev_frag[INVOKED]
                next_completed = next_frag[COMPLETED]
                next_invoked = next_frag[INVOKED]

                # Did the fragment start in this middle of this frag?
                if next_completed >= invoked >= next_invoked:
        
                    # Did it end inside the next frag (this frag
                    # would be a 'subset' of next_frag)? if so,
                    # we can just drop this frag, since next_frag
                    # accounts for its time
                    if next_completed >= completed:
                        break
                    else:
                        # This frag finished elsewhere; perhaps in a gap,
                        # or in the middle of another frag. Just place
                        # it in the list for now.
                        self.fragments.insert(i, new_frag)
                        break

                # Did the fragment start in the gap between the
                # previous frag and this next one?
                elif prev_invoked >= invoked >= next_completed:
                    # Just insert the frag; it doesn't matter if
                    # it ends in the gap, or if it ends in another
                    # gap, or in the middle of another fragment.
                    # We'll clean that up later.
                    self.fragments.insert(i, new_frag)
                    break

                # We haven't found a place yet; keep iterating
                prev_frag = next_frag
            else:
                # We couldn't find any place to put it.
                # Our algorithm should never fail like this!
                msg = "Could not place fragment %s in %s" % \
                        (new_frag, self.fragments)
                raise SequencingError(msg)

        # After we insert the fragment, adjust our boundary times
        self.absolute_start = self.fragments[-1][INVOKED]
        self.absolute_end = self.fragments[0][COMPLETED]

    def mergeOverlaps(self):
        # We start with a mostly-ordered set of time-fragment
        # tuples, except of the fact that neighbors can overlap
        # each other.
        #
        # Look at each node; if it overlaps with its neighbor
        # to the right, merge the two, and keep comparing.
        looking_at = 0
        len_fragments = len(self.fragments)

        # One or no fragments? Nothing to merge! Return now.
        if len_fragments < 2:
            return

        def overlaps(a, b):
            return b[COMPLETED] >= a[INVOKED]

        def merge(a, b):
            return (max(a[COMPLETED], b[COMPLETED]),
                    min(a[INVOKED], b[INVOKED]))

        i_examining = 0
        while i_examining < len_fragments - 1:
            this_frag = self.fragments[i_examining]

            i_comparison = i_examining + 1
            next_frag = self.fragments[i_comparison]

            # If there is no overlap, we can forget about this one.
            if not overlaps(this_frag, next_frag):
                i_examining += 1
                continue

            # There is an overlap; merge them
            new_frag = merge(this_frag, next_frag)

            # Delete this frag
            del self.fragments[i_examining]

            # Delete the next frag
            del self.fragments[i_examining]

            # Insertthe new frag
            self.fragments.insert(i_examining, new_frag)

            # Reduce the total length by 1
            len_fragments -= 1

            # Don't increment i_examining because we want
            # compare this newly merged fragment with its
            # new neighbor
            # I don't need this 'continue' here, but it's 
            # so far down from the 'while' that it's a nice
            # visual reminder that I'm iterating
            continue




class Cluster:
    """A container for all the agents."""

    def __init__(self):
        # Key = node name, Value = Agent object
        self.agents = {}

    def addTiming(self, timing):
        node = timing.getNode()
        agent = self.agents.get(node)
        if not agent:
            agent = self.agents[node] = Agent()

        agent.addTiming(timing)

    def mergeOverlaps(self):
        for agent in self.agents.values():
            agent.mergeOverlaps()

    def makeDiscrete(self):
        for agent in self.agents.values():
            agent.makeDiscrete()

    def getEarliestStart(self):
        start = -1
        for agent in self.agents.values():
            earliest_frag = agent.fragments[-1]
            if start == -1:
                start = earliest_frag = earliest_frag[INVOKED]
            else:
                start = min(start, earliest_frag[INVOKED])
        return start

    def getLatestEnd(self):
        end = -1
        for agent in self.agents.values():
            latest_frag = agent.fragments[0]
            end = max(end, latest_frag[COMPLETED])
        return end

    def calculateHistogram(self):
        # This is the histogram data we want.
        # Each key is the number of agents running concurrently,
        # and each value is the total time spent running at that
        # "concurrency"
        # Key = N, Value = Total Time
        #
        self.concurrency = {}

        # This magic dictionary will hold the latest single
        # time fragement from each agent. It allows us to scan
        # across all agents. If we pop a fragment from an agent
        # but there are no more fragments, we remove the agent name
        # from the dictionary.
        #
        # Key = agent name, Value = Time Frag (COMPLETED, INVOKED)
        self.frag_pops = {}

        def pop_agent_frag(name):
            frag = self.agents[name].pop()
            if frag == None:
                del self.frag_pops[name]
            else:
                self.frag_pops[name] = frag

        # Initialize!
        for name, agent in self.agents.items():
            frag = agent.pop()
            if frag:
                self.frag_pops[name] = frag

        def chop(time_slice_start, time_slice_end, frag):
            """See if a frag can be chopped into two pieces,
            if it overlaps with the time slice. Returns:
                (overlap_boolean, new_frag)

            If there is any overlap, overlap_boolean is True,
            otherwise False.

            If it overlaps completely, new_frag is None.

            If the old frag was chopped, the new, smaller
            frag is returned as new_frag.
            """

            # Is the time slice the same as this frag?
            if time_slice_start == frag[INVOKED] and \
                    time_slice_end == frag[COMPLETED]:
                return True, None

            # Do they overlap? XXX check this logic
            if time_slice_end >= frag[COMPLETED] > time_slice_start >= frag[INVOKED]:
                new_frag = (time_slice_start, frag[INVOKED])

                return True, new_frag

            # No overlap.
            return False, None

        # Run our algorithm until there are no more fragments
        # to analyze
        tot_time = 0.0

        minimum_slice_duration = pow(0.1, NUM_DECIMAL_PLACES)

        while self.frag_pops:
            # Look at all the frags and find the latest one
            # to complete, and the latest in invoked.
            # If some frags have times that match exactly
            # (either invoked or started), just pick one arbitrarily.
            latest_completed_frag = (-1.0, -1.0)
            latest_invoked_frag = (-1.0, -1.0)

            for name, frag in self.frag_pops.items():
                if frag[COMPLETED] > latest_completed_frag[COMPLETED]:
                    latest_completed_frag = frag

                if frag[INVOKED] > latest_invoked_frag[INVOKED]:
                    latest_invoked_frag = frag

            # We now have the latest time slice we want to chop off
            # from the end of all agents, where possible.
            time_slice_end = latest_completed_frag[COMPLETED]
            time_slice_start = latest_invoked_frag[INVOKED]
            slice_duration = time_slice_end - time_slice_start + \
                    minimum_slice_duration

            N = 0
            tot_time += slice_duration

            for name, frag in self.frag_pops.items():
                overlapped, smaller_frag = chop(time_slice_start,
                        time_slice_end, frag)

                if overlapped:
                    N += 1
                    if smaller_frag == None:
                        # We exhausted this agent's frag; pop a new one.
                        # (possible deleting the agent from the
                        # frag_pops hash, if its frags are depleted)
                        pop_agent_frag(name)
                    else:
                        # Replace the fag
                        self.frag_pops[name] = smaller_frag

            # Add to the bin
            if self.concurrency.has_key(N):
                self.concurrency[N] += slice_duration
            else:
                self.concurrency[N] = slice_duration

            # I don't need this 'continue', but it's a nice
            # visual reminder
            continue


        return self.concurrency


SECS_IN_HOUR = 60 * 60
SECS_IN_MINUTE = 60

def hms(total_seconds):
    """Given seconds, return a string of HhMmSs"""
    (hours, remainder_minutes) = divmod(total_seconds, SECS_IN_HOUR)
    (minutes, seconds) = divmod(remainder_minutes, SECS_IN_MINUTE)

    if hours > 0:
        return "%dh%dm%.3fs" % (hours, minutes, seconds)
    elif minutes > 0:
        return "%dm%.3fs" % (minutes, seconds)
    else:
        return "%.3fs" % (seconds,)
