import os
from .base_classes import Command,  ShellCommand

from setup.utils import (
    add_local_bin_path,
    create_postgres_user,
    install_poetry,
    resolve_template_file,
    shell_source,
    execute_shell,
    write_env_file,
    confirm_proceed,
    user_choice,
    make_dir_if_not_exists,
    wait_for_user_action,
)


commands_list = {
    "update": [
        "echo upgrade",
        "sudo apt-get upgrade -y",
        "echo dist-upgrade",
        "sudo apt-get dist-upgrade -y",
    ],
    # install python3.8
    # "python": [
    #     lambda caller: os.chdir("/opt"),
    #     "sudo wget https://www.python.org/ftp/python/3.8.10/Python-3.8.10.tgz",
    #     "sudo tar xzf Python-3.8.10.tgz",
    #     lambda caller: os.chdir("Python-3.8.10"),
    #     "sudo ./configure --enable-optimizations",
    #     "sudo make alt install",
    #     "echo python3 installed successfully !",
    # ],
    "sys_install": [
        lambda caller: os.chdir(caller.home_dir),
        "echo install system packages",
        Command(
            [
                f"sudo apt-get install -y {p}"
                for p in (
                    "zlib1g-dev build-essential libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev  python-setuptools python-pip python-smbus openssl libffi-dev python3-venv zip python3-distutils  software-properties-common redis postgresql postgresql-contrib libssl-dev curl python3-dev libpq-dev nginx nginx-common nginx-core git python-is-python3 binutils libproj-dev gdal-bin postgresql postgresql-contrib postgresql-client redis-server supervisor postgis postgresql-14-postgis-scripts postgresql-client-common"
                ).split()
            ],
            stop_in_error=False
        ),
        "echo packages installed successfully!",
    ],
    "pip": [
        "echo install pip",
        "curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py",
        "python3 get-pip.py",
        lambda caller: os.remove("get-pip.py"),
        lambda caller: add_local_bin_path(caller),
    ],
    "poetry": [
        "python3 -m pip install --upgrade setuptools",
        lambda caller: install_poetry(),
        # repeate
        lambda caller: add_local_bin_path(caller),
        # "curl -sSL https://install.python-poetry.org | python3 -",
        lambda caller: shell_source("~/.profile"),
    ],
    "configs": [
        "pip install dropbox python-dotenv",
        lambda caller: caller.load_configs(),
    ],
    "postgres": [
        "echo create db_user",
        create_postgres_user,
    ],
    "clone": [
        lambda caller: caller.configs,
        # install repo from git
        "echo install repo from git",
        # lambda caller: execute_shell(f"mkdir -p {caller.project_dir}"),
        lambda caller: os.chdir(caller.home_dir),
        lambda caller: ShellCommand(
            "git clone https://{{GITHUB_USERNAME}}:{{GITHUB_TOKEN}}@github.com/tabebqena/aqar.git"
            + " "
            + caller.project_dir
        )(caller),
    ],
    "env": [
        lambda caller: caller.configs,
        lambda caller: execute_shell(f"mkdir -p {caller.project_dir}"),
        lambda caller: os.chdir(caller.project_dir),
        write_env_file,
    ],
    "venv": [
        lambda caller: caller.configs,
        lambda caller: execute_shell(f"mkdir -p {caller.project_dir}"),
        lambda caller: os.chdir(caller.project_dir),
        lambda caller: f"{caller.python_path} -m venv {caller.venv_path}",
        lambda caller: shell_source(os.path.join(
            caller.venv_path, "bin/activate")),
        "poetry install",
    ],
    "shapely": [
        lambda caller: caller.configs,
        lambda caller: execute_shell(f"mkdir -p {caller.project_dir}"),
        lambda caller: os.chdir(caller.project_dir),
        lambda caller: execute_shell(
            f"{caller.pip_path} uninstall -y shapely"),
        "sudo apt install -y libgeos++-dev",
        lambda caller: execute_shell(
            f"{caller.pip_path} install --no-binary :all:  shapely"
        ),
    ],
    "django": [
        lambda caller: caller.configs,
        # execute_shell(f"mkdir -p {caller.project_dir}"),
        lambda caller: make_dir_if_not_exists(caller.project_dir),
        lambda caller: os.chdir(caller.project_dir),
        lambda caller: execute_shell(
            f"{caller.python_path} manage.py makemigrations",
        ),
        lambda caller: f"{caller.python_path} manage.py migrate",
        lambda caller: f"{caller.python_path} manage.py collectstatic",
        # create superuser
        lambda caller: user_choice(
            f"{caller.python_path} manage.py loaddata users",
            caller,
            "if you enter y or Y, the users fixture will be loaded, This may change your users table",
        ),
        # load necessary fixtures
        lambda caller: user_choice(
            f"{caller.python_path} manage.py loaddata saudia",
            caller,
            "if you enter y or Y, the saudia fixture will be loaded, This may change your country table",
        ),
        lambda caller: user_choice(
            f"{caller.python_path} manage.py loaddata region",
            caller,
            "if you enter y or Y, the region fixture will be loaded, This may change your region table",
        ),
        lambda caller: user_choice(
            f"{caller.python_path} manage.py loaddata governorate",
            caller,
            "if you enter y or Y, the governorate fixture will be loaded, This may change your governorate table",
        ),
        lambda caller: user_choice(
            f"{caller.python_path} manage.py loaddata fixtures/sites.json",
            caller,
            "if you enter y or Y, the sites fixture will be loaded, This may change your sites table",
        ),
    ],
    "gunicorn": [
        # gunicorn
        "echo create gunicorn log & change owner",
        lambda caller: caller.configs,
        lambda caller: execute_shell(f"mkdir -p {caller.project_dir}"),
        lambda caller: os.chdir(caller.project_dir),
        lambda caller: make_dir_if_not_exists("/var/log/gunicorn/"),
        lambda caller: make_dir_if_not_exists("/var/run/gunicorn/"),
        lambda caller: execute_shell(
            f"sudo chown -cR {caller.user} /var/log/gunicorn/"
        ),
        lambda caller: execute_shell(
            f"sudo chown -cR {caller.user} /var/run/gunicorn/"
        ),
        "echo build gunicorn.service",
        lambda caller: resolve_template_file(
            os.path.join(
                caller.project_dir, "config/gunicorn/gunicorn.service.template"
            ),
            caller.context,
        ),
        f"echo move '/config/gunicorn/gunicorn.service' & socket tp /etc/systemd/system",
        lambda caller: execute_shell(
            f"sudo cp {os.path.join( caller.project_dir,'config/gunicorn/gunicorn.socket')}  /etc/systemd/system/gunicorn.socket"
        ),
        lambda caller: execute_shell(
            f"sudo cp {os.path.join( caller.project_dir, 'config/gunicorn/gunicorn.service')} /etc/systemd/system/gunicorn.service"
        ),
        "echo run gunicorn",
        "sudo systemctl start gunicorn",
        "sudo systemctl enable gunicorn",
        "echo chech the gunicorn status for errors, if present: abort & type: sudo journalctl -u gunicorn.socket & sudo systemctl status gunicorn.socket",
        lambda caller: confirm_proceed("run_gunicorn"),
        "sudo systemctl daemon-reload",
    ],
    # todo chowner of static files
    "nginx": [
        "echo make nginx dir",
        lambda caller: caller.configs,
        lambda caller: execute_shell(f"mkdir -p {caller.project_dir}"),
        lambda caller: os.chdir(caller.project_dir),
        lambda caller: make_dir_if_not_exists("/etc/nginx/sites-available/"),
        lambda caller: resolve_template_file(
            "config/nginx/aqar.template", caller.context
        ),
        lambda caller: execute_shell(
            f"sudo cp {os.path.join(caller.project_dir, 'config/nginx/aqar')} /etc/nginx/sites-available/aqar"
        ),
        lambda caller: wait_for_user_action(
            "Go to /etc/nginx/nginx.conf & edit http { client_max_body_size 10M;  } or to another reasonable value, after this print enter"
        ),
        ShellCommand(
            "sudo ln -s /etc/nginx/sites-available/aqar /etc/nginx/sites-enabled/",
            stop_in_error=False,
        ),
        # backup default site
        ShellCommand(
            "sudo mv /etc/nginx/sites-available/default /etc/nginx/sites-available/__default",
            conditions=(
                lambda caller: os.path.exists(
                    "/etc/nginx/sites-available/default"),
            )

        ),

        # disble default site
        "sudo rm /etc/nginx/sites-enabled/default",
        "sudo systemctl restart nginx",
        "echo check the nginx errors above, if there is errors, correct it first",
        "sudo nginx -t",
        lambda caller: confirm_proceed("nginx"),
        "sudo systemctl reload nginx",
    ],
    "ufw": [
        # Allow connections to the server
        # "sudo ufw allow 8000",
        # "sudo ufw delete allow 8000",
        lambda caller: execute_shell(["sudo", "ufw", "allow", "nginx HTTP"]),
        lambda caller: execute_shell(["sudo", "ufw", "allow", "nginx HTTPS"]),
        lambda caller: execute_shell(["sudo", "ufw", "allow", "Nginx Full"]),
    ],
    "redis": [
        lambda caller: wait_for_user_action(
            """Navigate to /etc/redis/redis.conf
               CTRL+F to find 'supervised no' and replace with ‘supervised systemd’ and SAVE .
               """
        ),
        "sudo systemctl restart redis.service",
        "echo check redis status: sudo systemctl status redis",
        lambda caller: confirm_proceed("redis"),
        "echo check redis port: sudo netstat -lnp | grep redis",
        "sudo systemctl restart redis.service",
        lambda caller: confirm_proceed(
            "redis", "Check if the redis port is 6379"),
    ],
    "daphne": [
        lambda caller: caller.configs,
        lambda caller: execute_shell(f"mkdir -p {caller.project_dir}"),
        lambda caller: os.chdir(caller.project_dir),
        lambda caller: resolve_template_file(
            os.path.join(caller.project_dir,
                         "config/daphne/daphne.service.template"),
            caller.context,
        ),
        lambda caller: execute_shell(
            f"sudo cp {os.path.join(caller.project_dir,'config/daphne/daphne.service')} /etc/systemd/system/daphne.service"
        ),
        "sudo systemctl daemon-reload",
        "sudo systemctl start daphne.service",
        # "sudo systemctl status daphne.service",
        lambda caller: confirm_proceed(
            "daphne", "Check the dapne service status"),
        "sudo systemctl daemon-reload",
        "sudo systemctl start daphne.service",
        # Make it run on reboot
        "sudo systemctl enable daphne.service",
    ],
    "autoremove": [
        "echo autoremove && sudo apt autoremove -y",
    ],
}
