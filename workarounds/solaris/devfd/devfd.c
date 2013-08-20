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
 * We have no way to properly convert calls to freopen or freopen64.
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


/* If the given path is "/dev/fd/N" for some int N >= 0,
 * then return N; otherwise return -1.
 */
static int parse_path(char const *path)
{
    int saved_ern;
    int fd;
    char const *file;
    char *ep;

    if (strncmp(path, "/dev/fd/", 8) != 0) {
        return -1;
    }
    file = path + 8;

    saved_ern = errno;
    errno = 0;
    fd = strtol(file, &ep, 10);
    if (errno || ep == file || *ep || fd < 0) {
        fd = -1;
    }
    errno = saved_ern;

    return fd;
}


/* If we have not previously looked up the next definition of the given
 * symbol after the hook that we define ourselves, then do so and cache
 * the result in *cached_next.
 *
 * Accesses to pointer variables should be atomic, and therefore we
 * should see either NULL or a valid pointer when reading *cached_next,
 * meaning that a redundant lookup is the worst effect of a race.
 *
 * (You might add memory barrier instructions to speed up the pace at which
 * a cache update propagates to other processors, but first note how likely
 * it is that this function will be called by the first thread before it
 * creates the second thread.  Memory barriers might actually slow things.)
 */
static void *get_sym(void **cached_next, char const *name)
{
    void *next = *cached_next;

    if (! next) {
        next = dlsym(RTLD_NEXT, name);
        if (! next) {
            char const *err = dlerror();
            if (! err) {
                err = "dlerror returned NULL";
            }
            fprintf(stderr, "%s\n", err);
            exit(1);
        }
        *cached_next = next;
    }

    return next;
}


/* For functions similar to "open", set variable MODE to 0 unless the
 * variable FLAGS indicate a third argument was passed, in which case
 * extract that optional third argument.  MODE cannot be "ap".
 */
#define GET_OPEN_MODE(MODE, FLAGS)              \
    MODE = 0;                                   \
    if (FLAGS & O_CREAT) {                      \
        va_list ap;                             \
        va_start(ap, FLAGS);                    \
        MODE = va_arg(ap, mode_t);              \
        va_end(ap);                             \
    }


/* The type of the "open" function (both 32-bit and 64-bit).
 */
typedef int open_t(char const *, int, ...);

/* Forward declaration to ensure we match the function signature exactly.
 */
open_t open;

/* Replacement for the libc open() function.  Ordinarily just calls
 * the libc open() function, but if the specified path is "/dev/fd/N"
 * then short-circuits to dup().
 */
int open(char const *path, int flags, ...)
{
    static void *cached_next = 0;
    open_t *next;
    mode_t mode;
    int original_fd;

    GET_OPEN_MODE(mode, flags)

    original_fd = parse_path(path);
    if (original_fd == -1) {
        next = get_sym(&cached_next, "open");
        return (*next)(path, flags, mode);
    }

    return dup(original_fd);
}

#if _FILE_OFFSET_BITS == 32

open_t open64;

int open64(char const *path, int flags, ...)
{
    static void *cached_next = 0;
    open_t *next;
    mode_t mode;
    int original_fd;

    GET_OPEN_MODE(mode, flags)

    original_fd = parse_path(path);
    if (original_fd == -1) {
        next = get_sym(&cached_next, "open64");
        return (*next)(path, flags, mode);
    }

    return dup(original_fd);
}

#endif


/* The type of the "openat" function (both 32-bit and 64-bit).
 */
typedef int openat_t(int fd, char const *, int, ...);

openat_t openat;

int openat(int fd, char const *path, int flags, ...)
{
    static void *cached_next = 0;
    openat_t *next;
    mode_t mode;
    int original_fd;

    GET_OPEN_MODE(mode, flags)

    original_fd = parse_path(path);
    if (original_fd == -1) {
        next = get_sym(&cached_next, "openat");
        return (*next)(fd, path, flags, mode);
    }

    return dup(original_fd);
}

#if _FILE_OFFSET_BITS == 32

openat_t openat64;

int openat64(int fd, char const *path, int flags, ...)
{
    static void *cached_next = 0;
    openat_t *next;
    mode_t mode;
    int original_fd;

    GET_OPEN_MODE(mode, flags)

    original_fd = parse_path(path);
    if (original_fd == -1) {
        next = get_sym(&cached_next, "openat64");
        return (*next)(fd, path, flags, mode);
    }

    return dup(original_fd);
}

#endif


/* The type of the "fopen" function (both 32-bit and 64-bit).
 */
typedef FILE *fopen_t(char const *path, char const *mode);

fopen_t fopen;

FILE *fopen(char const *path, char const *mode)
{
    static void *cached_next = 0;
    fopen_t *next;
    int original_fd;
    int duped_fd;

    original_fd = parse_path(path);
    if (original_fd == -1) {
        next = get_sym(&cached_next, "fopen");
        return (*next)(path, mode);
    }

    duped_fd = dup(original_fd);
    if (duped_fd == -1) {
        return NULL;
    }
    return fdopen(duped_fd, mode);
}

#if _FILE_OFFSET_BITS == 32

fopen_t fopen;

FILE *fopen64(char const *path, char const *mode)
{
    static void *cached_next = 0;
    fopen_t *next;
    int original_fd;
    int duped_fd;

    original_fd = parse_path(path);
    if (original_fd == -1) {
        next = get_sym(&cached_next, "fopen64");
        return (*next)(path, mode);
    }

    duped_fd = dup(original_fd);
    if (duped_fd == -1) {
        return NULL;
    }
    return fdopen(duped_fd, mode);
}

#endif
