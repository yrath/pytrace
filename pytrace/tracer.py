# -*- coding: utf-8 -*-

import sys
import inspect
import fnmatch
import linecache
import os

from contextlib import contextmanager
from pytrace.util import colored, highlight_code


@contextmanager
def trace_execution(*args, **kwargs):
    tracer = Tracer(*args, **kwargs)
    yield tracer
    tracer.disable()


class Tracer(object):

    def __init__(self, trace_lines=False, traced_paths=None, max_depth=-1):
        """
        Initialize Tracer.

        Arguments:
          trace_line: Whether each line execution should be traced. Defaults to False.
          traced_paths: Only trace program execution in files contained in traced_paths.
              Allows globbing and defaults to all paths.
          max_depth: Maximum depth of stack that is still printed. Negative values
              mean no maximum. Defaults to -1.
        """
        self.stack = ["initial dir"]
        if traced_paths is None:
            self.traced_paths = ["*"]
        else:
            self.traced_paths = traced_paths
        self.trace_lines = trace_lines

        self.orig_tracefunc = sys.gettrace()
        sys.settrace(self.tracefunc)

        self.skip_paths = set()

        self.max_depth = max_depth
        self.last_trace = None

    def tracefunc(self, frame, event, arg):
        if frame is None:
            return self.tracefunc
        # skip previously skipped frame without invoking inspect for performance
        if frame.f_code in self.skip_paths:
            return None

        filename, lineno, function, code_context, index = inspect.getframeinfo(frame)
        filename = os.path.abspath(filename)

        # check if file in paths to be checked
        # only required if new function is called
        if event == "call" and not any(fnmatch.fnmatch(filename, path)
                for path in self.traced_paths):
            self.skip_paths.add(frame.f_code)
            return None

        # if we are in a method, figure out class
        try:
            cls = frame.f_locals['self'].__class__.__name__
            function = "{}.{}".format(cls, function)
        except (KeyError, AttributeError):
            pass

        msg = ""
        if event == "call":
            self.stack.append(function)
            msg += colored("--" * len(self.stack) + ">", color="green")
            msg += " call {} in {} from {}".format(
                colored(function),
                colored(filename, color="yellow"),
                colored(self.stack[-2]),
            )
            if self.last_trace is not None:
                msg += "\n" + " " * (2 * len(self.stack) + 1)
                msg += " {} {}, {}".format(
                    colored("as", color="yellow"),
                    highlight_code(linecache.getline(*self.last_trace)).strip(),
                    colored("l:{}".format(self.last_trace[1]), color="yellow")
                )
        elif event == "return":
            self.stack.pop(-1)
            msg += colored("  " * len(self.stack) + " <-", color="yellow")
            msg += " return from {} to {}".format(
                colored(function),
                colored(self.stack[-1])
            )
        elif event == "line" and code_context:
            if self.trace_lines:
                msg += " " * (2 * len(self.stack) + 1)
                msg += " {} {}".format(
                    colored("execute", color="yellow"),
                    highlight_code(code_context[0]).rstrip()
                )
        # only print message if stack does not exceed maximum depth
        if msg:
            if self.max_depth < 0 or len(self.stack) < self.max_depth:
                print(msg)
        # remember last step for call events, to determine where the call happens
        self.last_trace = (filename, lineno)

        return self.tracefunc

    def disable(self):
        sys.settrace(self.orig_tracefunc)
