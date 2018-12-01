# -*- coding: utf-8 -*-
from multiprocessing.managers import BaseManager, NamespaceProxy
from config_worker.main import PMonConfig


class PMConfManager(BaseManager):
    def PMonConfig(self):
        pass


class PMConfProxy(NamespaceProxy):
    _exposed_ = ('__getattribute__', '__setattr__', '__getattr__', '__delattr__')


PMConfManager.register('PMonConfig', PMonConfig, PMConfProxy)
