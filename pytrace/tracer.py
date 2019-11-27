# -*- coding: utf-8 -*-

import sys
import inspect
import fnmatch
import linecache
import os
import ast
import astunparse

from contextlib import contextmanager
from pytrace.util import colored, highlight_code, only_simple_types


@contextmanager
def trace_execution(*args, **kwargs):
    tracer = Tracer(*args, **kwargs)
    yield tracer
    tracer.disable()


class ASTValueGetter(ast.NodeTransformer):
    """
    Replace simple variables by their values in an AST.
    """
    def __init__(self, namespace):
        self.namespace = namespace

    def _to_ast_object(self, node, node_value):
        if sys.version_info.major >= 3:
            return ast.Constant(node_value)

        else:  # python 2
            if isinstance(node_value, bool):
                return ast.Name(bool, node.ctx)
            elif isinstance(node_value, (int, float, str)):
                return ast.Num(node_value)
            elif isinstance(node_value, list):
                return ast.List([self._to_ast_object(node, value) for value in node_value],
                    node.ctx)
            elif isinstance(node_value, tuple):
                return ast.Tuple([self._to_ast_object(node, value) for value in node_value],
                    node.ctx)

    def visit_Name(self, node):
        node_value = self.namespace.get(node.id, node)
        if only_simple_types(node_value):
            return self._to_ast_object(node, node_value)
        else:
            return node


class Tracer(object):

    def __init__(self, trace_lines=False, traced_paths=None, untraced_functions=None,
            parse_values=False, max_depth=-1):
        """
        Initialize Tracer.

        Arguments:
          trace_line: Whether each line execution should be traced. Defaults to False.
          traced_paths: Only trace program execution in files contained in *traced_paths*.
              Allows globbing and defaults to all paths.
          untraced_functions: Do not trace program execution in functions/methods
              contained in *untraced_functions*. Defaults to None.
          parse_values: Repeat function call trace with simple variables replaced by
              their values. Defaults to False.
          max_depth: Maximum depth of stack that is still printed. Negative values
              mean no maximum. Defaults to -1.
        """
        self.stack = ["initial dir"]
        if traced_paths is None:
            self.traced_paths = ["*"]
        else:
            self.traced_paths = traced_paths
        if untraced_functions is None:
            self.untraced_functions = []
        else:
            self.untraced_functions = untraced_functions

        self.trace_lines = trace_lines
        self.parse_values = parse_values

        self.orig_tracefunc = sys.gettrace()
        sys.settrace(self.tracefunc)

        self.skip_frames = set()

        self.max_depth = max_depth
        self.last_trace = {}  # last executed line for each depth
        self.last_namespace = {}  # corresponding namespace

    def tracefunc(self, frame, event, arg):
        if frame is None:
            return self.tracefunc
        # skip previously skipped frame without invoking inspect for performance
        if frame.f_code in self.skip_frames:
            return None

        filename, lineno, function, code_context, index = inspect.getframeinfo(frame)
        filename = os.path.abspath(filename)

        # check if file in paths to be checked
        # only required if new function is called
        if event == "call" and not any(fnmatch.fnmatch(filename, path)
                for path in self.traced_paths):
            self.skip_frames.add(frame.f_code)
            return None

        # check if function should be skipped
        # only required if new function is called
        if event == "call" and function in self.untraced_functions:
            self.skip_frames.add(frame.f_code)
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

            last_trace = self.last_trace.get(len(self.stack) - 1, None)
            if last_trace is not None:
                calling_line = linecache.getline(*last_trace)

                msg += "\n" + " " * (2 * len(self.stack) + 1)
                msg += " {} {}, {}".format(
                    colored("as", color="yellow"),
                    highlight_code(calling_line).strip(),
                    colored("l:{}".format(last_trace[1]), color="yellow")
                )

                # print the line also with variables replaced by their values
                if self.parse_values:
                    line_ast = ast.parse(calling_line.strip())
                    value_getter = ASTValueGetter(self.last_namespace[len(self.stack) - 1])
                    modified_ast = value_getter.visit(line_ast)
                    modified_line = astunparse.unparse(modified_ast)

                    msg += "\n" + " " * (2 * len(self.stack) + 1)
                    msg += " {} {}".format(
                        colored("with values", color="yellow"),
                        highlight_code(modified_line).strip(),
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
        # this (intendedly) skips intermediate untraced calls
        depth = len(self.stack) - 1 if event == "return" else len(self.stack)
        self.last_trace[depth] = (filename, lineno)
        if self.parse_values:
            self.last_namespace[depth] = dict(frame.f_globals, **frame.f_locals)

        return self.tracefunc

    def disable(self):
        sys.settrace(self.orig_tracefunc)
