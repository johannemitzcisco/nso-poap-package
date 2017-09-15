# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.application import Service

# ------------------------
# SERVICE CALLBACK EXAMPLE
# ------------------------
class ServiceCallbacks(Service):

    # The create() callback is invoked inside NCS FASTMAP and
    # must always exist.
    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')

        for device in service.device:
            self.log.info('Device (', device, ')')
            if root.devices.device.exists(device):
                self.log.info('Device (', device, ') registered, POAP state: ', root.poap.device[device].state)
                if 'ONLINE' == root.poap.device[device].state:
                    self.log.info('Configuring DNS')
                    vars = ncs.template.Variables()
                    vars.add('DEVICE', device)
                    template = ncs.template.Template(service)
                    template.apply('dns-service-template', vars)
                    self.log.info('DNS Configured')
                else:
                    if not root.kickers.data_kicker.exists(device):
                        self.log.info('Creating a watch on the device''s POAP status')
                        kicker = root.kickers.data_kicker.create(device)
                        kicker.monitor = "/poap/device[id='"+device+"']/state"
                        kicker.kick_node = "/dns-service[name='"+service.name+"']"
                        kicker.action_name = 'reactive-re-deploy'
            else:
                self.log.info('Device (', device, ') not registered and will not be configured')
                if not root.kickers.data_kicker.exists(device):
                    self.log.info('Creating a watch on the device''s POAP status')
                    kicker = root.kickers.data_kicker.create(device)
                    kicker.monitor = "/poap/device[id='"+device+"']/state"
                    kicker.kick_node = "/dns-service[name='"+service.name+"']"
                    kicker.action_name = 'reactive-re-deploy'

    # The pre_modification() and post_modification() callbacks are optional,
    # and are invoked outside FASTMAP. pre_modification() is invoked before
    # create, update, or delete of the service, as indicated by the enum
    # ncs_service_operation op parameter. Conversely
    # post_modification() is invoked after create, update, or delete
    # of the service. These functions can be useful e.g. for
    # allocations that should be stored and existing also when the
    # service instance is removed.

    # @Service.pre_lock_create
    # def cb_pre_lock_create(self, tctx, root, service, proplist):
    #     self.log.info('Service plcreate(service=', service._path, ')')

    @Service.pre_modification
    def cb_pre_modification(self, tctx, op, kp, root, proplist):
       self.log.info('Service premod(service=', kp, ') Operation:', op)
       with ncs.maapi.Maapi() as m:
           with ncs.maapi.Session(m, 'admin', 'admin'):
               with m.start_read_trans() as t:
                   root = ncs.maagic.get_root(t)
                   if 1 == op:
                       service = ncs.maagic.get_node(t, kp)
                       for s_device in service.device:
                           self.log.info('Service Device:', s_device)
                           if root.poap.device.exists(s_device):
                               self.log.info('Device state: ', root.poap.device[s_device].state, ' Device Registered: ', root.devices.device.exists(s_device))
                               if 'ONLINE' == root.poap.device[s_device].state and root.devices.device.exists(s_device):
                                   rootm = ncs.maagic.get_root(m)
                                   device = rootm.devices.device[s_device]
                                   output = device.ssh.fetch_host_keys()
                                   self.log.info('Fetch Host keys: ', output.result)
                                   sync_result = device.check_sync().result
                                   self.log.info('Device Synced: ', sync_result)
                                   if 'in-sync' !=  sync_result:
                                       output = device.sync_from()
                                       self.log.info('Sync Device: ', output.result)
                                       sync_result = device.check_sync().result
                               #    if 'in-sync' ==  sync_result:
                               #    service.re_deploy()
       return proplist 

    # @Service.post_modification
    # def cb_post_modification(self, tctx, op, kp, root, proplist):
    #     self.log.info('Service premod(service=', kp, ')')


# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class Main(ncs.application.Application):
    def setup(self):
        # The application class sets up logging for us. It is accessible
        # through 'self.log' and is a ncs.log.Log instance.
        self.log.info('Main RUNNING')

        # Service callbacks require a registration for a 'service point',
        # as specified in the corresponding data model.
        #
        self.register_service('dns-service-servicepoint', ServiceCallbacks)

        # If we registered any callback(s) above, the Application class
        # took care of creating a daemon (related to the service/action point).

        # When this setup method is finished, all registrations are
        # considered done and the application is 'started'.

    def teardown(self):
        # When the application is finished (which would happen if NCS went
        # down, packages were reloaded or some error occurred) this teardown
        # method will be called.

        self.log.info('Main FINISHED')
