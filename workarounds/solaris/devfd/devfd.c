/* Copyright (c) 2013, Electric Cloud, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 *   - Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *
 *   - Redistributions in binary form must reproduce the above copyright
 *     notice, this list of conditions and the following disclaimer in the
 *     documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

/* (As an historical note, the above license instantiates
 * the "BSD 2-Clause License" template that was presented
 * by the Open Source Initiative at
 *
 *   http://opensource.org/licenses/bsd-license.php
 *
 * on 2013-07-22.)
 */

/* Introduction:
 *
 * The lofs filesystem in Solaris 10 does not support /dev/fd/N correctly.
 * By contrast, you can use /dev/fd/N through the lofs filesystem in Solaris 9.
 * On Solaris 10 you may see errors such as:
 *
 *     ld: fatal: file /dev/fd/3: open failed: No such device or address
 *
 * In particular, this can happen when Solaris "dtrace" passes object
 * files to the linker in the form of /dev/fd/N pseudo-files.
 *
 * To work around this Solaris 10 bug, the shared library you can
 * build from this source file intercepts attempts to open /dev/fd/N
 * and converts them into dup() calls.
 *
 * This file is to be converted into a Solaris shared object library by:
 *
 *     gcc -m32 -c -O2 -Wall -fPIC devfd.c
 *     /usr/ccs/bin/ld -dy -G -o libdevfd.so devfd.o
 *
 * and then used via LD_PRELOAD to insert that shared object library
 * into the processes that you run:
 *
 *     LD_PRELOAD_32=./libdevfd.so dtrace ...
 *
 * Limitations:
 *
 * Currently this library makes no attempt to alter the read/write
 * access of the file descriptor, and in fact it may be impractical
 * to do so.  Thus there is no narrowing of the capabilities provided
 * by the program that created the file descriptor being dup()-ed.
 *
 * Currently this shared object library intercepts only the open()
 * function, and not other system functions that may bypass open().
 *
 * This shared library may interfere with other programs that
 * intercept system calls in user space, such as electrify.
 */

#include <dlfcn.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>


/* Print the context, then dlerror(), then exit(1).
 */
static void dldie(const char *context)
{
    char const *err = dlerror();
    if (! err) {
        err = "dlerror returned NULL";
    }
    fprintf(stderr, "%s: %s\n", context, err);
    exit(1);
}


/* Print the context, then strerror(errno), then exit(1).
 */
static void endie(char const *context)
{
    perror(context);
    exit(1);
}


/* The type of the "open" function.
 */
typedef int open_t(const char *, int, ...);

/* Forward declaration to ensure we match the function signature exactly.
 */
open_t open;

/* Replacement for the libc open() function.  Ordinarily just calls
 * the libc open() function, but if the specified path is "/dev/fd/N"
 * then short-circuits to dup().
 */
int open(const char *path, int flags, ...)
{
    static open_t *cached_open = 0;
    open_t *original_open;
    int original_fd;
    mode_t mode;
    va_list ap;

    /* Do not even attempt to access the mode argument unless
     * we know that the caller (should have) supplied it.
     */
    mode = 0;
    if (flags & O_CREAT) {
        va_start(ap, flags);
        mode = va_arg(ap, mode_t);
        va_end(ap);
    }

    /* If we have not previously looked up the next "open" after this one,
     * then do so and cache the result.  Accesses to pointer variables should
     * be atomic, and therefore we should see either NULL or a valid pointer,
     * meaning that a redundant lookup is the worst effect of a race.
     *
     * (You might add memory barrier instructions to speed up the pace at which
     * a cache update propagates to other processors, but first note how likely
     * it is that this function will be called by the first thread before it
     * creates the second thread.  Memory barriers might actually slow things.)
     */
    original_open = cached_open;
    if (! original_open) {
        original_open = dlsym(RTLD_NEXT, "open");
        cached_open = original_open;
    }

    if (strncmp(path, "/dev/fd/", 8) != 0) {
        /* Not opening /dev/fd/N, so pass through to next "open".
         */
        return (*original_open)(path, flags, mode);
    }

    errno = 0;
    original_fd = atoi(path + 8);
    if (errno) {
        endie(path);
    }

    return dup(original_fd);
}
