# -*- coding: utf-8 -*-

import sys
import inspect
import fnmatch
import linecache

from pytrace.util import colored


class Tracer(object):

    def __init__(self, basepaths=None, trace_lines=False, traced_paths=None, max_depth=-1):
        self.stack = ["__main__", "Tracer.__init__"]
        if traced_paths is None:
            self.traced_paths = ["*"]
        else:
            self.traced_paths = traced_paths

        self.orig_tracefunc = sys.gettrace()
        sys.settrace(self.tracefunc)

        self.max_depth = -1
        self.last_trace = None

    def tracefunc(self, frame, event, arg):
        if frame is not None:
            filename, lineno, function, code_context, index = inspect.getframeinfo(frame)

            # check if file in paths to be checked
            if not any(fnmatch.fnmatch(filename, path) for path in self.traced_paths):
                return self.tracefunc

            try:
                cls = frame.f_locals['self'].__class__.__name__
                function = "{}.{}".format(cls, function)
            except (KeyError, AttributeError):
                pass

            msg = ""
            if event == "call":
                self.stack.append(function)
                msg += colored("--" * len(self.stack) + ">", color="green")
                msg += " call {} from {} in {}".format(
                    colored(function),
                    colored(self.stack[-2]),
                    colored(filename, color="blue"),
                )
                if self.last_trace is not None:
                    msg += "\n" + " " * (2 * len(self.stack) + 1)
                    msg += " as {}".format(
                        colored(linecache.getline(*self.last_trace).strip(), color="blue")
                    )
            elif event == "return":
                self.stack.pop(-1)
                msg += colored("<" + "--" * len(self.stack), color="yellow")
                msg += " return from {} to {}".format(
                    colored(function),
                    colored(self.stack[-1])
                )
            if msg:
                if self.max_depth < 0 or len(self.stack) < self.max_depth:
                    print(msg)
            self.last_trace = (filename, lineno)

        return self.tracefunc

    def disable(self):
        sys.settrace(self.orig_tracefunc)
