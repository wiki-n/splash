# -*- coding: utf-8 -*-
from __future__ import absolute_import
import re, os, ConfigParser
from PyQt4.QtNetwork import QNetworkProxyFactory, QNetworkProxy
from splash.utils import getarg, BadRequest


class BlackWhiteQNetworkProxyFactory(QNetworkProxyFactory):
    """
    Proxy factory that enables non-default proxy list when
    requested URL is matched by one of whitelist patterns
    while not being matched by one of the blacklist patterns.
    """
    def __init__(self, blacklist=None, whitelist=None, proxy_list=None):
        self.blacklist = blacklist or []
        self.whitelist = whitelist or []
        self.proxy_list = proxy_list or []
        super(BlackWhiteQNetworkProxyFactory, self).__init__()

    def queryProxy(self, query=None, *args, **kwargs):
        protocol = unicode(query.protocolTag())
        url = unicode(query.url().toString())
        if self.shouldUseDefault(protocol, url):
            return self._defaultProxyList()

        return self._customProxyList()

    def shouldUseDefault(self, protocol, url):
        if not self.proxy_list:
            return True

        if protocol != 'http':  # don't try to proxy https
            return True

        if any(re.match(p, url) for p in self.blacklist):
            return True

        if any(re.match(p, url) for p in self.whitelist):
            return False

        return bool(self.whitelist)

    def _defaultProxyList(self):
        return [QNetworkProxy(QNetworkProxy.DefaultProxy)]

    def _customProxyList(self):
        return [
            QNetworkProxy(QNetworkProxy.HttpProxy, *args)
            for args in self.proxy_list
        ]


class SplashQNetworkProxyFactory(BlackWhiteQNetworkProxyFactory):
    """
    """
    GET_ARGUMENT = 'proxy'

    def __init__(self, proxy_rules_path, request):
        proxy_rules_path = os.path.abspath(proxy_rules_path)
        filename = getarg(request, self.GET_ARGUMENT, None)
        if not filename:
            params = [], [], []
        else:
            ini_path = os.path.abspath(os.path.join(proxy_rules_path, filename))
            if not ini_path.startswith(proxy_rules_path + os.path.sep):
                # security check
                params = [], [], []
            else:
                params = self._parseIni(ini_path)
        super(SplashQNetworkProxyFactory, self).__init__(*params)


    def _parseIni(self, ini_path):
        parser = ConfigParser.ConfigParser(allow_no_value=True)
        if not parser.read(ini_path):
            return [], [], []

        blacklist = _get_lines(parser, 'rules', 'blacklist', [])
        whitelist = _get_lines(parser, 'rules', 'whitelist', [])
        proxy_params = dict(parser.items('proxy'))
        proxy_list = [(
            proxy_params['host'],
            int(proxy_params['port']),
            proxy_params.get('username'),
            proxy_params.get('password'),
        )]

        return blacklist, whitelist, proxy_list


def _get_lines(config_parser, section, option, default):
    try:
        lines = config_parser.get(section, option).splitlines()
        return [line for line in lines if line]
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
        return default
