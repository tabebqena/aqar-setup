from inspect import isfunction
import json
import os
import stat
import subprocess
import sys
import traceback
from typing import Union, List
import re
from cryptography.fernet import Fernet


def __build_rekey(key):
    return "{0}[ ]*{1}[ ]*{2}".format("{{", key, "}}")


def resolve_text(command: Union[str, List[str]], ctx: dict):
    if isinstance(command, str):
        for k, v in ctx.items():
            built_key = __build_rekey(k)
            command = re.sub(built_key, str(v), command)
        return command
    elif isinstance(command, list):
        rv = []
        for part in command:
            for k, v in ctx.items():
                part = re.sub(__build_rekey(k), str(v), part)
            rv.append(part)
        return rv
    else:
        raise RuntimeError(
            "{0} is not string nor list of strings".format(command))


def resolve_template_file(input_path, ctx: dict):
    target_path = os.path.join(
        os.path.dirname(input_path),
        os.path.basename(input_path).replace(".template", ""),
    )
    with open(input_path, "r") as template:
        content = resolve_text(template.read(), ctx)
        with open(target_path, "w") as target:
            target.write(content)
            print(f"File created: {target}")


def add_local_bin_path(caller):
    home = caller.home_dir
    with open(os.path.join(home, ".profile"), "r+") as f:
        p = os.path.join(home, ".local/bin")
        expr = f'\nexport PATH="{p}":$PATH\n'
        if expr not in f.read():
            f.write(expr)


def install_poetry():
    proc = subprocess.run(
        "curl -sSL https://install.python-poetry.org ".strip().split(),
        stdout=subprocess.PIPE,
    )
    rv = subprocess.run(["python3", "-c", bytes.decode(proc.stdout)])

    return rv


def shell_source(script):
    """Sometime you want to emulate the action of "source" in bash,
    settings some environment variables. Here is a way to do it."""
    pipe = subprocess.Popen(". %s; env" %
                            script, stdout=subprocess.PIPE, shell=True)
    output = bytes.decode(pipe.communicate()[0])
    env = {}
    env = dict((line.split("=", 1) for line in output.splitlines()))
    os.environ.update(env)


def _download(
    api_key=None,
    api_secret=None,
    access_token=None,
):
    """Download a file.
    Return the bytes of the file, or None if it doesn't exist.
    """
    import dropbox

    dbx = dropbox.Dropbox(
        oauth2_access_token=access_token or input(
            "Enter dropbox access token: "),
        app_key=api_key or input("Enter dropbox API key: "),
        app_secret=api_secret or input("Enter dropbox API Secret: "),
    )
    try:
        md, res = dbx.files_download("/env")
    except dropbox.exceptions.HttpError as err:
        print("*** HTTP error", err)
        raise (err)
    data = res.content
    return data


def _decrypt(key, text: Union[str, bytes]):
    cipher_suite = Fernet(key)
    return cipher_suite.decrypt(text)


def _get_encryption_key():
    return input(
        "ENTER The encryption key -The key that used to encrypt the secret configs-  (Hint: get it from the drive): "
    )


def get_remote_env(api_key=None, api_secret=None, access_token=None, key=None):
    api_key = api_key or os.environ.get("api_key")
    api_secret = api_secret or os.environ.get("api_secret")
    access_token = access_token or os.environ.get("access_token")
    encryption_key = key or os.environ.get("key")
    # print(encryption_key)
    data = _download(
        api_key,
        api_secret,
        access_token,
    )
    data = _decrypt(encryption_key or _get_encryption_key(), data)
    data = bytes.decode(data)
    return json.loads(data)


def load_configs(api_key=None, api_secret=None, access_token=None, key=None):

    return get_remote_env(
        api_key=api_key,
        api_secret=api_secret,
        access_token=access_token,
        key=key,
    )


def execute_shell(command: Union[str, list]):
    if isinstance(command, str):
        return subprocess.run(
            command.strip().split(),
            #   stderr=subprocess.PIPE
        )
    elif isinstance(command, list):
        return subprocess.run(command)
    else:
        raise Exception("shell command should be string or list of strings")


def create_postgres_user(caller):
    path = os.path.join(caller.current_dir, "create.sql")
    with open(path, "w") as f:
        txt = f"""
#!/bin/sh

psql -U postgres postgres <<OMG
 CREATE USER {caller.configs['DB_USER']} password '{caller.configs['DB_PASSWORD']}';
OMG
"""
        f.write(txt)
        print(txt)

    os.chmod(path, stat.S_IEXEC)
    print(f"sh {path}")
    rv = execute_shell(f"sh {path}")

    if rv.returncode > 0:
        text = rv.stderr or rv.stdout

        if text:
            text = bytes.decode(text)
        else:
            text = ""
        raise Exception(f"Error: {text}")
    else:
        os.remove(path)


def write_env_file(caller):
    cfgs = caller.configs
    path = caller.env_path
    cfgs["DEBUG"] = False

    with open(path, "w") as f:
        f.writelines([f"{key}={value}\n" for key, value in cfgs.items()])


def make_dir_if_not_exists(path):
    if os.path.exists(path):
        return
    execute_shell(f"sudo mkdir -pv {path}")


def confirm_proceed(index, message=""):
    if message:
        print(message)
    p = input("Proceed? \ntype 'Y' or 'y' to proceed, any other key to abort: ")
    if p.lower() != "y":
        print(f"next time, you can type up {index} to start from this step")
        sys.exit("aborted by user\n")


def user_choice(command, caller, message=""):
    if message:
        print(message)
    p = input("Proceed? \ntype 'Y' or 'y' to proceed, any other key to abort: ")
    if p.lower() != "y":
        print("aborted by user")
        return
    else:
        return execute_command(command, caller)


def wait_for_user_action(message):
    print(message)
    print(
        "\nWait for your action, After finishing the following instructions, press ENTER"
    )
    input(
        "\nWait for your action, After finishing the following instructions, press ENTER"
    )


def execute_command(cmd, caller, stop_on_error=False):

    try:
        if isinstance(cmd, str):
            rv = execute_shell(cmd)
            if rv.returncode != 0:
                print("Error Command: ", cmd)
                if rv.stdout:
                    print(rv.stdout)
                if rv.stderr:
                    print(rv.stderr)
                if stop_on_error:
                    raise Exception(
                        f"The last command {cmd} end with error")

        if isinstance(cmd, list):
            errors = []
            for c in cmd:
                try:
                    rv = execute_command(c, caller, stop_on_error)
                except:
                    if stop_on_error:
                        raise
                    else:
                        errors.append(e)
            if errors:
                for error in errors:
                    print(traceback.format_exception(error))
                confirm_proceed("", "Procees after this errors?")

        elif callable(cmd):
            return cmd(caller=caller)
    except Exception as e:
        raise e
