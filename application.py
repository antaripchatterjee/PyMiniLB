from pymsgprompt.logger import perror, pwarn, pinfo
from pymsgprompt.prompt import ask
from socket import gethostbyname, gaierror
from datetime import datetime
import argparse
import math
import re
import os
import getpass
import string
import shutil
import sqlite3
from datetime import datetime

from pyminilb.actions.create import CreateApp
from pyminilb.actions.start import StartApp
from pyminilb.actions.runtime import SingleSiteAppRunner, ProcManager

# create_app_params = {}


def is_gitrepo(create_app_params, answer):
    create_app_params['IS_GITREPO'] = answer == 'yes'

def is_multisite(create_app_params, answer):
    create_app_params['IS_MULTISITE'] = answer == 'yes'

def add_framework(create_app_params, framework):
    if framework == 'Others':
        framework = ''
    create_app_params['REQUIRED_MODULES'] = [framework]
    if framework.strip().lower() == 'flask':
        create_app_params['REQUIRED_MODULES'].extend(['flask-sqlalchemy', 'flask-restful'])
    create_app_params['BASE_FRAMEWORK'] = framework

def add_license(create_app_params, _license):
    create_app_params['APP_LICENSE'] = _license

def main():
    create_app_params = {}
    __version__ = '0.0.3'
    parser = argparse.ArgumentParser(prog="PyMiniLB", description="A python based mini load balancer")
    parser.add_argument('--version', '-v', action='version', version="%(prog)s {0}\n".format(__version__))
    parser.add_argument('-newapp', action='store', default=None, type=str,
        help="create a new application", dest='app_name')
    parser.add_argument('-host', '--h', action='store', default='localhost', type=str,
        help="specify host name of the load balancer", dest='app_host') 
    parser.add_argument('-port', '--p', action='store', default=6543, type=int,
        help="specify the port number of the load balanacer", dest='app_port') 
    parser.add_argument('-instance', '--i', action='append', default=None,
        help="creates a new instance of the child application", dest='instances') 
    parser.add_argument('-instance-range', '--ir', action='append', default=None, type=str,
        help="create a range of instances of child application", dest='instance_range')
    parser.add_argument('-yes', '--y', action='store_true', default=False,
        help="whether to execute the venv.sh script once it is created", dest='exec_script')

    parser.add_argument('-startapp', action='store_true', default=False,
        help="start an application", dest='startapp')
    parser.add_argument('-site-config', '--sc', action='store', default='site-config.xml',
        help="specify site config file explicitely", dest='site_config')

    parser.add_argument('-stopapp', action='store_true', default=False,
        help="stop an application", dest='stopapp')
    parser.add_argument('-reloadapp', action='store_true', default=False,
        help="reload an application", dest='reloadapp')
    result = parser.parse_args()
    
    application_action = map(lambda v: 1 if v else 0, [
        result.stopapp,
        result.reloadapp,
        result.startapp,
        result.app_name is not None
    ])
    int_value = 0
    for i, v in enumerate(list(application_action)[::-1]):
        int_value += (2**i * v)
    try:
        if math.ceil(math.log2(int_value)) != math.floor(math.log2(int_value)):
            perror('Multiple action support has not been implemented yet')
            exit(-1)
    except ValueError:
        perror('Application action can not be empty')
        exit(-1)

    if int_value == 1:
        try:
            app_host = gethostbyname(result.app_host)
        except gaierror:
            pwarn('host ip is not valid\nChanging it to default value `localhost`')
            app_host = '127.0.0.1'
        app_port = result.app_port
        if app_port not in range(1, 2**16):
            pwarn('port_number is not valid\nChanging to default value `6543`')
            app_port = 6543
        instances = []
        if result.instances is not None:
            pat = r'^\s*([0-9a-z][a-z0-9\-]*)?\s*\:\s*(\d+)\s*$'
            for instance in result.instances:
                m = re.match(pat, instance)
                if m is not None:
                    inst_host, inst_port = m.groups()
                    if inst_host is None:
                        inst_host = 'localhost'
                    if inst_host.strip() == '':
                        inst_host = 'localhost'
                    port_ = int(inst_port)
                    try:
                        if port_ not in range(1, 2**16):
                            raise gaierror('invalid port number %d'%port_)
                        instances.append((gethostbyname(inst_host), port_))
                    except gaierror:
                        pwarn('instance `{0}:{1}` is not valid, ignoring'.format(inst_host, port_))
                else:
                    pwarn('instance `{0}` is not valid, ignoring'.format(instance))
        if result.instance_range is not None:
            pat = r'^\s*([0-9a-z][a-z0-9\-]*)?\s*\:\s*(\d+)(\.\.|\*)(\d+)\s*$'
            for instance in result.instance_range:
                m = re.match(pat, instance)
                if m is not None:
                    inst_addr, inst_ports_lhs, inst_oper, inst_ports_rhs = m.groups()
                    if inst_addr is None:
                        inst_addr = 'localhost'
                    if inst_addr.strip() == '':
                        inst_addr = 'localhost'
                    if inst_oper == '*':
                        for port_id in range(int(inst_ports_rhs)):
                            port_ = int(inst_ports_lhs) + port_id
                            try:
                                if port_ not in range(1, 2**16):
                                    raise gaierror('invalid port number %d'%port_)
                                instances.append((gethostbyname(inst_addr), port_))
                            except gaierror:
                                pwarn('instance `{0}:{1}` is not valid, ignoring'.format(inst_addr, port_))
                    else:
                        for port_ in range(int(inst_ports_lhs), int(inst_ports_rhs) + 1):
                            try:
                                if port_ not in range(1, 2**16):
                                    raise gaierror('invalid port number %d'%port_)
                                instances.append((gethostbyname(inst_addr), port_))
                            except gaierror:
                                pwarn('instance `{0}:{1}` is not valid, ignoring'.format(inst_addr, port_))
                else:
                    pwarn('instance `{0}` is not valid, ignoring'.format(instance))
        unique_instance_addrs = list(dict.fromkeys(instances))
        create_app_params['APP_NAME'] = result.app_name
        create_app_params['APP_DIR'] = os.path.abspath(os.path.join(os.path.relpath('./'), result.app_name))
        create_app_params['APP_HOST'] = app_host
        create_app_params['APP_PORT'] = app_port
        create_app_params['INSTANCES'] = unique_instance_addrs
        create_app_params['APP_CREATE_DATE'] = datetime.now().strftime(r'%d-%b-%Y')
        create_app_params['APP_CREATE_TIME'] = datetime.now().strftime(r'%H:%M:%S')
        
        create_app_params['AUTHOR_NAME'] = ask('Author name?', timestamp=True, default=getpass.getuser())
        create_app_params['AUTHOR_EMAIL'] = ask('Author email?', timestamp=True)
        create_app_params['COPYRIGHT_OWNER'] = ask('Copyright owner?', timestamp=True, default=create_app_params['AUTHOR_NAME'])
        create_app_params['APP_VERSION'] = ask('Application version?', timestamp=True, default='0.0.1')
        create_app_params['ENTRY_POINT'] = ask('Entry point?', timestamp=True, default='app.py')
        ask('Which framework support do you want to have?', timestamp=True, default='Flask',
            choices=['Flask', 'Django', 'AIOHTTP', 'Tornado', 'Pyramid', 'web2py', 'Others'],
            on_success=lambda q, a: add_framework(create_app_params, a))
        _venv = ''
        for char in result.app_name:
            if char in string.digits or char in string.ascii_letters:
                _venv += char
            else:
                _venv += '_'
        _package = _venv
        _venv += "_env"
        if create_app_params['BASE_FRAMEWORK'].lower() in ('flask', ):
            create_app_params['PACKAGE_NAME'] = ask('Package Name?', timestamp=True, default=_package)
        create_app_params['VENV_NAME'] = _venv
        ask('Does your application support multisite?', timestamp=True, default='no',
            choices=['yes', 'no'], on_success=lambda q, a: is_multisite(create_app_params, a))
        ask('Please specify the license.', timestamp=True, default='MIT',
            choices=['MIT', 'BSD-3', 'BSD', 'GNU-GPL', 'GNU-LGPL', 
                'Freeware', 'Shareware', 'EULA', 'Copyleft', 
                'Apache License', 'Mozilla Public', 'Microsoft Public',
                'Eclipse Public', 'Unlicense', 'Others'], on_success=lambda q, a: add_license(create_app_params, a))
        ask('Do you want to initialize a git repo?', timestamp=True, default='yes',
            choices=['yes', 'no'], on_success=lambda q, a: is_gitrepo(create_app_params, a))
        create_app_params['OS'] = os.sys.platform.upper()
        create_app_params['BASH_PATH'] = shutil.which('bash')
        create_app_params['PYTHON_EXE'] = os.path.basename(os.sys.executable)
        create_app_params['instances'] = unique_instance_addrs
        newappcreator = CreateApp(create_app_params)
        pinfo('Crating your app.. Please wait for sometime')
        newappdir = newappcreator.create_fs()
        if newappdir is not None:
            venv_script_path = newappcreator.get_venv_script(newappdir)
            if venv_script_path is not None:
                if result.exec_script:
                    newappcreator.exec_venv(venv_script_path)
                else:
                    if ask('Do you want to execute the venv script now?',
                        timestamp=True, choices=['yes', 'no'], default='no').lower().startswith('y'):
                        newappcreator.exec_venv(venv_script_path)
                    else:
                        pinfo(f'Please execute the venv script from {create_app_params["APP_DIR"]}')
            else:
                perror('Could not get venv script')
    elif int_value == 2: # startapp
        cwd = os.getcwd()
        config_file = os.path.abspath(os.path.join(cwd, 'config', result.site_config))
        if os.path.isfile(config_file):
            app = StartApp(config_file)
            app.validate()
            appmanager = app.startapp()
            if os.sys.platform.upper() == 'WIN32':
                script_cmd = ['.\launch.ps1']
            else:
                script_cmd = ['./launch.sh']
            if not os.path.isfile(os.path.abspath(script_cmd[-1])):
                perror(f'Could not find {os.path.abspath(script_cmd[-1])}')
                exit(-1)
            commands = script_cmd + appmanager.args
            if not appmanager.auto_lb:
                procs = [ProcManager(appmanager.ref, { 'proc' : SingleSiteAppRunner().run(
                    commands,
                    os.getcwd(),
                    dict(HOST=instance['@host'], PORT=instance['@port'],
                        LOGTIMESTAMP=datetime.now().strftime(r'%Y-%m-%d_%H:%M:%S'))
                    ),
                    'host' : instance['@host'],
                    'port' : instance['@port']
                }) for instance in appmanager.instances]
            else:
                procs = [ProcManager(appmanager.ref, { 'proc' : SingleSiteAppRunner().run(
                    commands,
                    os.getcwd(),
                    dict(HOST=instance['@host'], PORT=instance['@port'],
                        LOGTIMESTAMP=datetime.now().strftime(r'%Y%m%d_%H%M%S'))
                    ),
                    'host' : instance['@host'],
                    'port' : instance['@port']
                }) for instance in appmanager.instances[:appmanager.init_lb]]
            # print(procs)
            for proc in procs:
                proc.get_cpid()
        else:
            perror(f'Could not find site config file, {config_file}')
    elif int_value == 4: # stopapp
        pass
    else: # reloadapp
        pass
if __name__ == "__main__":
    main()