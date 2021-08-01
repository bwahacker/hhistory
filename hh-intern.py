#!/usr/bin/python3 
#
# Some scribbles towards contextual history
#
# Copyright (c) 2021, Mitch Haile.
# 
# MIT License
#

import os
import sys

from collections import defaultdict


def usage():
    print("$0 <path> -- show commands run when the given path was the CWD")
    print("e.g, $0 . -- shows the commands run in this directory.")
    sys.exit(2)
    return

def parse_history():
    homeDir = os.environ['HOME']
    cmap = defaultdict(list)

    with open("%s/.myhistory" % homeDir, "r") as fp:
        history = fp.readlines()
        thisDir = os.environ["HOME"]

        for i in range(len(history)):
            line = history[i]

            if line[-1] == "\n":
                line = line[:-1]
            
            #print("\n\n", i, ":", thisDir, ": ", line)

            dirPath = None
            # FIXME: we miss things like ls && cd ~, etc...
            if line.startswith("cd "):
                dirPath = line[3:]
            elif line.startswith("pushd "):
                dirPath = line[6:]
            elif line == "pushd":
                # Well.... sigh.
                # Could build a list of where we think files are and try to infer the cwd from there...
                
                dirPath = None

            #print("thisDir = __%s__; new command = %s" % (thisDir, line))
            
            if dirPath is not None:
                #print("We have a cd event!!!!!")

                if dirPath.find("~") >= 0:
                    dirPath = os.path.expanduser(dirPath)

                if not dirPath.startswith("/"):
                    # nothing is easy - we have to use where we were.
                    if thisDir is not None:
                        newPath = thisDir + "/" + dirPath
                        newPath = os.path.realpath(newPath)
                        # see if it exists...
                        if not os.path.exists(newPath):
                            #print("%s: thisDir = %s, can't figure out where %s is - not %s" % (i, thisDir, dirPath, newPath))
                            continue
                        else:
                            dirPath = newPath
                else:
                    dirPath = os.path.realpath(dirPath)
                # endif

                # add an entry.
                if thisDir is not None:
                    # FIXME: should we add a cd away from the current dir to the history of this dir? Could be! Let's try it.
                    #if thisDir.find("mitch/test") > 0:
                    #    print("%s: ADDING: %s <-- %s" % (i, thisDir, line))
                    cmap[thisDir].append(line)
                # endif
                thisDir = dirPath
            else:
                # we don't have a path, we're just appending...
                #if thisDir.find("mitch/test") > 0:
                #    print("%s: ADDING: %s <-- %s" % (i, thisDir, line))

                if thisDir is not None:
                    cmap[thisDir].append(line)
            
            # endif

            
        # endfor
    # endif

    return cmap


def main():
    if len(sys.argv) == 1:
        usage()

    arg = sys.argv[1]
    if arg == ".":
        cmap = parse_history()
        if False:
            ks = list(cmap.keys())
            ks.sort()
            for k in ks:
                print("DIRS:", k)
        # look for commands we had in this dir.
        cwd = os.getcwd()
        print(cwd)

        cmds = cmap.get(cwd)
        if cmds is None:
            print("No commands found for this directory :-(")
            sys.exit(1)
        # endif

        for entry in cmds:
            print("   %s" % entry)


if __name__ == "__main__":
    main()

