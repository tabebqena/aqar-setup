import importlib
from inspect import isfunction
from typing import Any, List
import traceback

from .utils import (
    resolve_text,
    execute_shell,
    confirm_proceed,
)


class Command:
    def __init__(self, command, stop_in_error=True, *args, **kwargs) -> None:
        self.command = command
        self.stop_in_error = stop_in_error
        self.args = args
        self.kwargs = kwargs

    def resolve(self, caller):
        return self.command

    def __call__(self, caller=None):
        cmd = self.resolve(caller)
        try:
            if isinstance(cmd, str):
                rv = execute_shell(cmd)
                if rv.returncode != 0:
                    print("Error Command: ", cmd)
                    print(rv.stdout)
                    print(rv.stderr)
                    if self.stop_in_error:
                        raise Exception(f"The last command {cmd} end with error")

            elif isfunction(cmd):
                cmd(*self.args, **self.kwargs)
            else:
                raise Exception(f"can't understand command {cmd}")
        except Exception as e:
            raise Exception(f"Error in {cmd}") from e


class ShellCommand(Command):
    def resolve(self, caller):
        rv = resolve_text(self.command, caller.context)
        print("resolved to:", rv)
        return rv


class CallableCommand(Command):
    def __init__(self, command: str, from_instance=False, *args, **kwargs) -> None:
        self.command = command
        self.args = args
        self.kwargs = kwargs

    def resolve(self, caller):
        if isfunction(self.command):
            return self.command

        else:
            parts = self.command.split(".")
            mod_name, name = ".".join(parts[:-1]), parts[-1]
            module = importlib.import_module(mod_name)
            if module:
                var = getattr(module, name)
                if var:
                    return var
        raise Exception(f"can't import {name} from {mod_name} : {module}")


class ShellCommandList:
    def __init__(
        self,
        stop_in_error=False,
        commands_list=[],
    ):
        self.commands_list: List[str] = commands_list
        self.stop_in_error = stop_in_error

    def __call__(self, caller=None, *args: Any, **kwds: Any) -> Any:
        errors = []
        for command in self.commands_list:
            try:
                ShellCommand(command, *args, **kwds)(caller)
            except Exception as e:
                if self.stop_in_error:
                    raise
                else:
                    errors.append(e)  # traceback.print_exc()
        if errors:
            for error in errors:
                print(traceback.format_exception(error))
            confirm_proceed("", "Procees after this errors?")
