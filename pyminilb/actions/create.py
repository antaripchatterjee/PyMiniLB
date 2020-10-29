import subprocess
from jinja2 import FileSystemLoader, Environment
from pyminilb.settings import APP_TEMPLATES_DIR
import json
import os
from pymsgprompt.logger import perror, pinfo, pwarn
import shutil

class CreateApp():
    def render(self, path, **params):
        return self.environment.get_template(path).render(**params)
    def __internal_create_fs(self, parent, folder_struct):
        if os.path.isdir(parent):
            try:
                folder_name = folder_struct['folder-name']
                new_directory = os.path.abspath(os.path.join(parent, folder_name))
                os.makedirs(new_directory)
                if 'files' in folder_struct.keys():
                    if isinstance(folder_struct['files'], (list, tuple)):
                        for file in folder_struct['files']:
                            if not isinstance(file, dict):
                                perror('file should be dictionary, got %s'%(type(file).__name__, ))
                                return None
                            else:
                                if 'template' not in file.keys():
                                    file['template'] = False
                                elif file['template'] == None:
                                    file['template'] = False
                                if not isinstance(file['template'], bool):
                                    perror('template should be a boolean value, got %s'%(type(file['template']).__name__, ))
                                    return None
                                if 'file-name' not in file.keys():
                                    perror('file-name is not specified in the folder structure')
                                    return None
                                file_name = file['file-name']
                                if not isinstance(file_name, str):
                                    perror('file-name must be a string value, got %s'%(type(file_name).__name__, ))
                                    return None
                                file_fullpath = os.path.abspath(os.path.join(new_directory, file_name))
                                with open(file_fullpath, 'w') as target:
                                    if file['template']:
                                        if 'template-path' not in file.keys():
                                            pwarn('template-path is not available')
                                        elif not isinstance(file['template-path'], str):
                                            pwarn('invalid value for template-path, must be str but got %s'%(type(file['template-path']).__name__, ))
                                        else:
                                            template_path = file['template-path']
                                            template_content = self.render(template_path, **self.params)
                                            target.write(template_content)
                    else:
                        perror('invalid value for `files`, expected a list, got %s'%(type(folder_struct['files']).__name__, ))
                        return None
                if 'folders' in folder_struct.keys():
                    if isinstance(folder_struct['folders'], (list, tuple)):
                        for folder in folder_struct['folders']:
                            if self.__internal_create_fs(new_directory, folder) is None:
                                perror('Could not directory %s'%(
                                    os.path.abspath(os.path.join(new_directory, folder['folder-name']))
                                ))
                    else:
                        perror('folders must be a list or tuple, but got %s'%(type(folder_struct['folders']).__name__, ))
                        return None
            except KeyError:
                perror('folder-name is not specified in the folder structure')
                return None
            except OSError:
                perror('child directory `%s` already exists'%(new_directory, ))
                return None
        else:
            return None
        return new_directory
    def create_fs(self):
        path_to_template = '{0}-templates/fstructs/{0}.json'.format(self.params['BASE_FRAMEWORK'].lower())
        fs_json_content = self.render(path_to_template,
            ENTRY_POINT=self.params['ENTRY_POINT'],
            PACKAGE_NAME=self.params['PACKAGE_NAME'],
            APP_NAME=self.params['APP_NAME']
        )
        fs_json = json.loads(fs_json_content)
        
        return self.__internal_create_fs(os.path.dirname(self.params['APP_DIR']), fs_json)
    def create_venv_sh(self, newappdir):
        if os.sys.platform.upper() == 'WIN32':
            return None
        else:
            path_to_template = '/venv-templates/venv.sh.jinja2'
            shell_script_content = self.render(path_to_template,
                BASH_PATH=shutil.which('bash'),
                PYTHON_EXE=os.path.basename(os.sys.executable),
                VENV_NAME=self.params['VENV_NAME'],
                REQUIRED_MODULES=self.params['REQUIRED_MODULES'],
                PACKAGE_NAME=self.params['PACKAGE_NAME'],
                GITREPO=self.params['IS_GITREPO']
            )
        venv_script_path = os.path.abspath(os.path.join(newappdir, 'venv.sh'))
        with open(venv_script_path, 'w') as venv_script:
            venv_script.write(shell_script_content)
        return venv_script_path
    def exec_venv(self, script_path):
        cwd = os.path.abspath(os.path.dirname(script_path))
        script_name = os.path.basename(script_path)
        if os.sys.platform.upper() == 'WIN32':
            pass
        else:
            command = [f'./{script_name}']
        try:
            pinfo('Executing venv.sh')
            status = subprocess.run(command, cwd=cwd, check=True, text=True, shell=True,
                stderr=subprocess.STDOUT, stdout=subprocess.PIPE, encoding='utf-8')
            if status.stdout is not None:
                pinfo(status.stdout)
            if status.stderr is not None:
                pwarn(status.stderr)
            if status.returncode == 0:
                pinfo('App has been created successfully')
        except subprocess.CalledProcessError as e:
            perror(f'Could not create new app, exited with return code {e.returncode}, reason {e.output}')
            return False
        return True

    def __init__(self, params):
        self.params = params
        fsloader = FileSystemLoader(APP_TEMPLATES_DIR)
        self.environment = Environment(loader=fsloader)
        self.environment.trim_blocks = True
        self.environment.lstrip_blocks = True

