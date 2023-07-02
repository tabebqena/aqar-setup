import importlib
from inspect import isfunction
from typing import Any, List
import traceback

from .utils import (
    execute_command,
    resolve_text,
    execute_shell,
    confirm_proceed,
)


class Command:
    def __init__(self, commands, stop_in_error=True, conditions=(), *args, **kwargs) -> None:
        if isinstance(commands, (list, tuple)):
            self.commands = commands
        else:
            self.commands = (commands,)
        self.stop_in_error = stop_in_error
        self.conditions = conditions
        self.args = args
        self.kwargs = kwargs

    def resolve(self, command, caller):
        return command

    def __call__(self, caller=None):
        if self.conditions:
            matched = True
            for index, condition in enumerate(self.conditions):
                _matched = condition(caller)
                print(index, condition, _matched)
                if not _matched:
                    print(f"Condition not matched on {index}: {condition}")
                matched = matched and _matched
            if not matched:
                print("skip command as not all conditions are matched")
                return
        for command in self.commands:
            command = self.resolve(command, caller)
            try:
                execute_command(command, caller, self.stop_in_error)

            except Exception as e:
                raise Exception(f"Error in {command}") from e


class ShellCommand(Command):
    def resolve(self, command, caller):
        rv = resolve_text(command, caller.context)
        print("resolved to:", rv)
        return rv
