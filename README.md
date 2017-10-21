# reduce-tree

## What is this?

In order to provide support for different architectures and peripherals, the
codebase of a modern operating system's kernel spans hundreds of megabytes in
size and consists of thousands of source code files. Upon compilation, only a
small part of this code makes it into the final executable.

When auditing such a codebase, one would naturally want to concentrate on the
code that is relevant to their target architecture and feature subset, and
filter out any inapplicable code paths.

This utility deduces from the build process which C source and header files
are relevant to the final build product, and produces a reduced source tree
consisting of these files.

The resulting codebase can be fed to other utilities, for further simplification
(e.g elimination of unused preprocessor directives) or cross-referencing.

This is not a novel concept. There are similar tools by [Jann Horn](https://git.thejh.net/?p=cleanmysourcetree.git)
and [Joshua J. Drake](https://github.com/jduck/lk-reducer), which are based on
the inotify subsystem of the Linux kernel. This tool makes use of access and modification
times of files, as they behave under `relatime` mount option. For more details check the
"How it works?" section.

This tool will not work as intended on filesystems mounted with `noatime`/`norelatime` options.


## How do I use it?

Let's assume you want to reduce the codebase of Linux 4.13.4, which resides under `~/src/linux-4.13.4`, and you want to store the reduced source tree
under `~/src/linux-4.13.4-reduced`.

Before compiling the kernel, you should prepare the files' metadata:

```
$ ./reduce-tree.py --prepare --src ~/src/linux-4.13.4
```

Proceed to build the kernel:

```
$ cd ~/src/linux-4.13.4
$ make x86_64_defconfig
$ make -j16
```

When the build is completed, create the target directory and produce the reduced source tree:

```
$ mkdir ~/src/linux-4.13.4-reduced
$ ./reduce-tree.py --collect --src ~/src/linux-4.13.4 --dst ~/src/linux-4.13.4-reduced
```

Now `~/src/linux-4.13.4-reduced` contains the directory tree consisting only out of .c and .h files
that were used during the buid process.


## What do I need?

A modern Linux distribution, default mount options, and Python 2.7. Theoretically, this should also
work on other open-source UNIX-based operating systems, but it was not tested as of this writing.


## How it works?

This tools uses the access and modification times of files and their behaviour under `relatime` mount option.

A long time ago, every file access was triggering an update of its access time. Due to increased disk writes,
this was causing performance issues. People came up with the `noatime` mount option to prevent these issues,
but this option broke applications that were relying on this functionality. Eventually the `relatime` option
was introduced. With this option, a file's access time is only updated if the previous access time was earlier
than the current modify or change time. Nowadays, this option is part of the default mount options.

In order to deduce which files were used in the build, this script sets the modification time of all `.c` and `.h`
files in the source tree to current time, and the access time to 48 hours before that. Next, the build process is
started. Any files that are accessed (i.e opened) during this process are forced to update their access time. After
the build completes, we just traverse the source tree and collect any `.c` and `.h` files that have modification time
earlier than access time, and copy them to our destination.

