"""fake api using araalictl underneath
    api = api.API()

    alerts, page, status = api.get_alerts(args.count, args.ago)
    assets, status = api.get_assets(args.zone, args.app, args.ago)
    links, status = api.get_links(args.zone, args.app, args.svc, args.ago)
    insights, status = api.get_insights(args.zone)
"""
import datetime
import os
import platform
import sys
from . import utils
import yaml

g_debug = False

class API:
    def __init__(self):
        progdir = os.path.dirname(os.path.abspath(__file__))
        if os.path.isfile(progdir + "/bin/araalictl"):
            self.cmdline = progdir + "/bin/araalictl"
        else:
            self.cmdline = progdir + "/bin/" + {
                                                "Linux": "araalictl.linux-amd64",
                                                "Darwin": "araalictl.darwin-amd64"
                                               }[platform.system()]

    def get_alerts(self, count=None, ago=None, token=None, tenant=None):
        """get alerts"""

        if tenant is None: tenant = utils.cfg["tenant"]
        if count is None: count = 1000

        if not ago:
            start_time = 0
            end_time = 0
        else:
            ago = dict([utils.make_map(a) for a in ago.split(",")])
            start_time = datetime.datetime.now() - datetime.timedelta(**ago)
            end_time = datetime.datetime.now()

            start_time = int(start_time.timestamp())
            end_time = int(end_time.timestamp())
 
        cmd = "-starttime %s" % (start_time)
        cmd += " -endtime %s" % (end_time)
        if token:
            cmd += " -paging-token %s" % token

        tstr = " -tenant=%s " % (tenant) if tenant else ""
        rc = utils.run_command("%s api -fetch-alerts %s -count %s %s" % (
                            self.cmdline, cmd, count, tstr),
                         debug=g_debug, result=True, strip=False)

        token = None
        objs = yaml.load(rc[1], yaml.SafeLoader)
        if objs:
            token=objs[-1].get("paging_token", None)

        return objs, token, rc[0]

    def get_assets(self, zone=None, app=None, ago=None, tenant=None):
        """Get assets for a zone (required) and app (optional)
            Usage: assets, status = api.get_assets()
        """
        if not ago:
            ago = "days=1"
        ago = dict([utils.make_map(a) for a in ago.split(",")])
        start_time = datetime.datetime.now() - datetime.timedelta(**ago)
        end_time = datetime.datetime.now()

        cmd = "-starttime %s" % (int(start_time.timestamp()))
        cmd += " -endtime %s" % (int(end_time.timestamp()))
        if zone: cmd += " -zone %s" % zone
        if app: cmd += " -app %s" % app
        if tenant is None: tenant = utils.cfg["tenant"]
        if tenant: cmd += " -tenant %s" % tenant

        rc = utils.run_command("%s api %s -fetch-compute" % (
            self.cmdline, cmd), debug=g_debug, result=True, strip=False)
        return yaml.load(rc[1], yaml.SafeLoader), rc[0]

    def get_links(self, zone=None, app=None, svc=None, ago=None, tenant=None):
        """Get links for a zone and app, or svc"""
        assert svc is not None or zone is not None and app is not None

        if tenant is None: tenant = utils.cfg["tenant"]
        tstr = " -tenant=%s " % (tenant) if tenant else ""
        if svc:
            tstr += " -service=%s " % (svc)
        else:
            tstr += " -zone=%s -app=%s " % (zone, app)
    
        if not ago:
            ago = "days=1"
        ago = dict([utils.make_map(a) for a in ago.split(",")])
        start_time = datetime.datetime.now() - datetime.timedelta(**ago)
        end_time = datetime.datetime.now()
        tstr += " -starttime %s" % (int(start_time.timestamp()))
        tstr += " -endtime %s" % (int(end_time.timestamp()))

        rc = utils.run_command("%s api -fetch-links %s" % (self.cmdline, tstr),
                         debug=g_debug, result=True, strip=False)
        return yaml.load(rc[1], yaml.SafeLoader), rc[0]

    def get_insights(self, zone=None, tenant=None):
        """Get insights for a zone (optional)"""
        cmd = ""
        if zone: cmd += " -zone %s" % zone
        if tenant is None: tenant = utils.cfg["tenant"]
        if tenant: cmd += " -tenant %s" % tenant

        rc = utils.run_command("%s api %s -fetch-insights" % (
            self.cmdline, cmd), debug=g_debug, result=True, strip=False)
        return yaml.load(rc[1], yaml.SafeLoader), rc[0]