import subprocess

class ProcManager(object):
    def get_cpid(self):
        out = self.proc['proc'].stdout.read()
        print(out)
    def __init__(self, ref: str, proc: dict):
        self.proc = proc
        self.ref = ref


class SingleSiteAppRunner():
    def run(self, commands, cwd, env):
        proc = subprocess.Popen(
            commands, bufsize=1, text=True, universal_newlines=True, shell=True, env=env, cwd=cwd,
            start_new_session=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        return proc
