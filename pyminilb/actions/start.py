import xmltodict

class SingleSiteAppManager():
    def __init__(self, **kwargv):
        self.ref = kwargv['ref']
        self.appdir = kwargv['appdir']
        self.mhost = kwargv['mhost']
        self.mport = kwargv['mport']
        self.args = kwargv['args']
        self.auto_lb = kwargv['auto_lb']
        self.init_lb = kwargv['init_lb']
        self.inc_lb = kwargv['inc_lb']
        self.thresold = kwargv['thresold']
        self.instances = kwargv['instances']

class StartApp():
    def _start_single_siteapp(self) -> SingleSiteAppManager:
        single_site_app = self.configuration['SingleSiteApp']
        reference = single_site_app['@reference']
        app_dir = single_site_app['@appdir']
        main_server = single_site_app['Server']
        main_server_host = main_server['@host']
        main_server_port = int(main_server['@port'])
        try:
            command_line_args = single_site_app['CommandLineArgs']
            arguments = command_line_args['Argument']
            if isinstance(arguments, str):
                arguments = [arguments]
        except KeyError:
            command_line_args = {'Argument' : []}
            arguments = command_line_args['Argument']
        instances = single_site_app['Instances']
        auto_lb = instances['@auto']
        init_lb = int(instances['@init-load'])
        increment = int(instances['@increment-by'])
        thresold_req = int(instances['@thresold'])
        true_instances = list(filter(lambda instance: instance['@active'] == 'true', instances['Instance']))
        return SingleSiteAppManager(
            ref=reference,
            appdir=app_dir,
            mhost=main_server_host,
            mport=main_server_port,
            args=arguments,
            auto_lb=auto_lb,
            init_lb=init_lb,
            inc_lb = increment,
            thresold=thresold_req,
            instances=true_instances
        )
    def _start_multi_siteapp(self):
        pass
    def startapp(self) -> SingleSiteAppManager:
        app_method = self.configuration['AppMethod']
        if app_method['@method'] == 'single-site':
            return self._start_single_siteapp()
        elif app_method['@method'] == 'multi-site':
            return self._start_multi_siteapp()
        else:
            raise NotImplementedError(f'{app_method["@method"]} has still not implemented.')
    def validate(self):
        try:
            with open(self.site_config_filename) as site_config:
                siteapp = xmltodict.parse(site_config.read())
                self.configuration = siteapp['Configuration']
            return None
        except Exception as e:
            return f'{e}'
    def __init__(self, site_config_filename):
        self.site_config_filename = site_config_filename