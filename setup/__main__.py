import argparse
import getpass
import os
import sys
from typing import Any, Dict

from .utils import execute_command, load_configs
from .commands_list import commands_list


def parse_args():
    parser = argparse.ArgumentParser(prog="Server Up")
    parser.add_argument(
        "-s",
        "--steps",
        help="enumerate The steps to be executed, example: -s step1 step2",
        nargs="*",
        default=[],
    )

    parser.add_argument(
        "-x", "--exclude", nargs="*", help="steps to be excluded", default=[]
    )
    # parser.add_argument(
    #     "-xx", "--exclude_command", nargs="*", help="commands to be excluded", default=[]
    # )

    parser.add_argument(
        "-f",
        "--first",
        nargs="?",
        help="start the execetion from this step",
        default=None,
    )

    parser.add_argument(
        "-l",
        "--last",
        nargs="?",
        help="end the execetion after this step",
        default=None,
    )

    parser.add_argument(
        "-u", "--user", nargs="?", help="The user name", default=getpass.getuser()
    )

    parser.add_argument(
        "--home", nargs="?", help="steps to be skipped", default=os.path.expanduser("~")
    )

    parser.add_argument(
        "--api-key",
        help="dropbox api key",
    )

    parser.add_argument(
        "--api-secret",
        help="dropbox api secrets",
    )

    parser.add_argument(
        "--access",
        help="dropbox access token",
    )

    parser.add_argument(
        "--key",
        help="encryption keys",
    )

    parser.add_argument(
        "--conf",
        help="configuration file path, file that contains access_token, api_key, api_secret and key",
    )

    parser.add_argument(
        "-p",
        "--print",
        help="print commands only.",
        action="store_true",
    )

    args = parser.parse_args(sys.argv[1:])
    if (args.first or args.last) and args.steps:
        raise Exception(
            "wrong options, You can't use range --first | --last with --steps"
        )

    if args.conf:
        conf = {}
        with open(args.conf, "r") as f:
            lines = f.readlines()
            for line in lines:
                k, v = line.strip().split("=", 1)
                conf[k] = v
        if not args.access:
            args.access = conf["access"]
        if not args.key:
            args.key = conf["key"]
        if not args.api_secret:
            args.api_secret = conf["api_secret"]

        if not args.api_key:
            args.api_key = conf["api_key"]
    return args


class Up:
    def __init__(
        self,
        commands=[],
        user=None,
        home_dir=None,
        key=None,
        api_key=None,
        api_secret=None,
        access_token=None,
    ) -> None:
        if not commands:
            raise Exception("Empty commands list, Nothing to execute")
        self.commands = commands
        self._user = user
        self._home_dir = home_dir
        self.key = key
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self._configs = None
        self._project_dir = None
        self._python_path = None
        self._pip_path = None
        self._venv_path = None
        self._env_path = None

    def load_configs(self):
        self._configs = load_configs(
            self.api_key, self.api_secret, self.access_token, self.key
        )

    @property
    def configs(
        self,
    ) -> Dict[str, Any]:
        if self._configs is None:
            self.load_configs()
        return self._configs

    @property
    def user(self) -> str:
        if not self._user:
            self._user = input("Enter the username: ")

        return self._user

    @property
    def home_dir(self) -> str:
        if not self._home_dir:
            self._home_dir = input("Enter the home dir: ")

        return self._home_dir

    @property
    def context(self):
        ctx = {}
        configs = self._configs
        if configs is not None:
            ctx.update(configs)
        ctx.update({"HOME_DIR": self.home_dir, "USER": self.user})
        # print("Context: ", ctx)
        return ctx

    @property
    def project_dir(self):
        if self._project_dir is None:
            self._project_dir = os.path.abspath(
                os.path.join(
                    self.home_dir,
                    self.configs["PROJECT_DIRNAME"],
                )
            )
        return self._project_dir

    @property
    def python_path(self):
        if self._python_path is None:
            self._python_path = os.path.join(
                self.project_dir,
                self.configs["VENV_DIRNAME"],
                "bin",
                "python3",
            )
        return self._python_path

    @property
    def pip_path(self):
        if self._pip_path is None:
            self._pip_path = os.path.join(
                self.project_dir,
                self.configs["VENV_DIRNAME"],
                "bin",
                "pip",
            )
        return self._pip_path

    @property
    def venv_path(self):
        if self._venv_path is None:
            self._venv_path = os.path.join(
                self.project_dir,
                self.configs["VENV_DIRNAME"],
            )
        return self._venv_path

    @property
    def env_path(self):
        if self._env_path is None:
            self._env_path = os.path.join(
                self.project_dir,
                ".env",
            )
        return self._env_path

    def run(self):
        for s, cmd_list in self.commands.items():
            print(f"Step: {s}")

            for cmd in cmd_list:
                execute_command(cmd, self)
            f = open("step", "w")
            f.write(s)
            f.close()


if __name__ == "__main__":
    # argv = sys.argv[1:]
    args = parse_args()
    print(args)
    if args.first or args.last:
        _keys = list(commands_list.keys())

        if getattr(args, "first", None):
            first = _keys.index(args.first)
        else:
            first = 0
        if getattr(args, "last", None):
            last = _keys.index(args.last)
        else:
            last = -1
        steps = _keys[first:last]
        _commands = {s: commands_list[s] for s in steps if s not in args.exclude}

    elif args.steps:
        _commands = {s: commands_list[s] for s in args.steps if s not in args.exclude}

    else:
        _commands = commands_list

    if args.print:
        for step, commands in _commands.items():
            print("Step:", step)
            for command in commands:
                print(" " * 4, command)
            print("\n")
        sys.exit(0)

    print(list(_commands.keys()))

    proceed = input("press 'y' or 'Y' to continue, any key to abort: ")

    if proceed.lower().strip() != "y":
        sys.exit("Aborted by user")

    up = Up(
        commands=_commands,
        user=args.user,
        home_dir=args.home,
        key=args.key,
        api_key=args.api_key,
        api_secret=args.api_secret,
        access_token=args.access,
    )

    up.run()
