"""
A file-like object that concatentes multiple files together
in sequence, making them look like a single file.
"""

import os
import stat

READ = "r"
READ_BINARY = "rb"

ABSOLUTE = 0

class ConcatenatedFile:
    UNKNOWN = -1
    IMPOSSIBLE = -1

    def __init__(self, filenames, mode):
        if len(filenames) == 0:
            raise ValueError("Need at least one file name.")

        # Save the initiliaztion data for ourselves.
        self.filenames = filenames
        self.mode = mode
        self.num_files = len(self.filenames)

        # Open the first file, so we can throw an exception
        # _now_ if the file doesn't exist or there are permission problems
        self.fh = open(self.filenames[0], mode)

        # True if we are open, False if closed.
        self.currently_open = True

        # 'fh' is currently for the 0th file
        self.fh_index = 0

        # We call our "position" the "super-position", which
        # has a maximum of the sum of the sizes of all the files.
        # It starts at 0, because start at the beginning of the 0th
        # file.
        self.super_pos = 0

        # Analyze the file sizes
        self.superpos_start = [self.UNKNOWN for f in self.filenames]
        self.superpos_end = [self.UNKNOWN for f in self.filenames]

        # Start at 0.
        self.superpos_start[0] = 0

        for i, filename in enumerate(self.filenames):
            if i > 0:
                self.superpos_start[i] = self.superpos_end[i-1] + 1
            size = os.stat(filename)[stat.ST_SIZE]
            self.superpos_end[i] = self.superpos_start[i] + size - 1

        # Our super-size
        self.super_size = self.superpos_end[self.num_files-1] + 1

    def _find_index_from_super_pos(self, super_pos):
        for i in range(self.num_files):
            if super_pos >= self.superpos_start[i] and \
                    super_pos <= self.superpos_end[i]:
                return i
        # Beyond the end?
        return self.IMPOSSIBLE

    def tell(self):
        return self.super_pos

    def close(self):
        if self.currently_open:
            self.fh.close()
            self.currently_open = False

    def seek(self, seek_super_pos, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            new_abs_super_pos = seek_super_pos
        elif whence == os.SEEK_CUR :
            new_abs_super_pos = self.super_pos  + seek_super_pos
        elif whence == os.SEEK_END :
            # seek_super_pos must be 0 or negative!
            if seek_super_pos > 0:
                raise ValueError("Seek argument must be 0 or negative with SEEK_END")
            new_abs_super_pos = self.super_size + seek_super_pos

        # Which file?
        seek_index = self._find_index_from_super_pos(new_abs_super_pos)
        if seek_index == self.IMPOSSIBLE:
            # If it's beyond our max length, we go to the last file
            seek_index = self.num_files - 1

        # Do we need to change files?
        if seek_index != self.fh_index:
            self.fh.close()
            self.fh_index = seek_index
            self.fh = open(self.filenames[self.fh_index])

        # seek to the absolute position in that file
        offset = new_abs_super_pos - self.superpos_start[self.fh_index]
        self.fh.seek(offset)
        self.super_pos = new_abs_super_pos


    def read(self, num_bytes=UNKNOWN):
        if num_bytes == self.UNKNOWN:
            return self._read_everything()
        else:
            data = self.fh.read(num_bytes)
            if len(data) < num_bytes:
                while True:
                    num_bytes -= len(data)
                    if num_bytes == 0:
                       break

                    result = self._go_to_next_file()
                    if result == False:
                        break

                    new_data = self.fh.read(num_bytes)
                    data += new_data
                    if len(new_data) == num_bytes:
                        break
            return data

    def _read_everything(self):
        # Read the rest of this filehandle
        data = self.fh.read()

        # Any more file handles?
        while self.fh_index < self.num_files - 1:
            self.fh.close()
            self.fh_index += 1
            self.fh = open(self.filenames[self.fh_index])
            data += self.fh.read()

        # Return the result
        return data

    def _go_to_next_file(self):
        """Change fh to the next file. Returns True if successful,
        or False if impossible."""
        if self.fh_index + 1 >= self.num_files:
            return False
        self.fh.close()
        self.fh_index += 1
        self.fh = open(self.filenames[self.fh_index])
        return True
