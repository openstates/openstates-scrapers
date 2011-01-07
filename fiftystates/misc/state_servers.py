#!/usr/bin/env python
"""
Print a breakdown of what web servers state legislatures are using.
"""
import httplib2

urls = {
    'ak': 'http://www.legis.state.ak.us/',
    'al': 'http://alisondb.legislature.state.al.us/acas/',
    'ar': 'http://www.arkleg.state.ar.us/',
    'az': ('http://www.azleg.gov/FormatDocument.asp?inDoc=/legtext/49leg/'
           '1r/bills/'),
    'ca': 'http://www.leginfo.ca.gov/',
    'co': 'http://www.leg.state.co.us/',
    'ct': 'http://cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp',
    'de': 'http://legis.delaware.gov/',
    'fl': 'http://www.flsenate.gov/Session/',
    'ga': 'http://www.legis.ga.gov/legis/2003_04/sum/sum/sb1.htm',
    'hi': 'http://www.capitol.hawaii.gov/session2010/',
    'ia': 'http://www.legis.state.ia.us/index.html',
    'id': 'http://www.legislature.idaho.gov/idstat/TOC/IDStatutesTOC.htm',
    'il': 'http://www.ilga.gov/',
    'in': 'http://www.in.gov/legislative/index.htm',
    'ks': 'http://www.kslegislature.org/legsrv-legisportal/index.do',
    'ky': 'http://www.lrc.ky.gov/senate/senmembers.htm',
    'la': 'http://www.legis.state.la.us/billdata/',
    'me': 'http://www.mainelegislature.org/legis/bills/search_ps.asp',
    'ma': 'http://www.mass.gov/legis/bills/',
    'md': 'http://mlis.state.md.us',
    'me': 'http://www.mainelegislature.org/legis/bills/',
    'mi': 'http://www.legislature.mi.gov/mileg.aspx?page=MM%d-%d&chapter=3',
    'mn': 'https://www.revisor.leg.state.mn.us/revisor/pages/search_status/',
    'mo': 'http://www.senate.mo.gov',
    'ms': 'http://billstatus.ls.state.ms.us',
    'mt': 'http://leg.mt.gov/css/default.asp',
    'nc': 'http://www.ncga.state.nc.us',
    'nd': 'http://www.legis.nd.gov',
    'ne': 'http://nebraskalegislature.gov/',
    'nh': 'http://www.gencourt.state.nh.us/bill_status/Results.aspx',
    'nj': 'http://www.njleg.state.nj.us',
    'nm': 'http://www.nmlegis.gov',
    'nv': 'http://www.leg.state.nv.us/',
    'ny': 'http://assembly.state.ny.us/',
    'oh': 'http://www.legislature.state.oh.us/',
    'ok': 'http://www.lsb.state.ok.us/',
    'or': 'http://www.leg.state.or.us/',
    'pa': 'http://www.legis.state.pa.us/cfdocs/',
    'ri': 'http://www.rilin.state.ri.us/',
    'sc': 'http://www.scstatehouse.gov/',
    'sd': 'http://legis.state.sd.us/sessions/',
    'tn': 'http://www.legislature.state.tn.us/',
    'tx': 'http://www.senate.state.tx.us/75r/senate/senmem.htm',
    'ut': 'http://www.le.state.ut.us/asp/roster/',
    'va': 'http://leg1.state.va.us/%s/mbr/MBR.HTM',
    'vt': 'http://www.leg.state.vt.us/database/status/summary.cfm?Bill=S.0292&amp;Session=2010',
    'wa': 'http://www.leg.wa.gov/pages/home.aspx',
    'wi': 'http://www.legis.state.wi.us/2009/data/DE9AB2hst.html',
    'wv': 'http://www.legis.state.wv.us/Bill_Status/',
    'wy': 'http://legisweb.state.wy.us/',
    }

http = httplib2.Http()

servers = {}
powereds = {}

apache = 0
iis = 0
lotus = 0
sun = 0
na = 0

for state, url in urls.items():
    resp = http.request(url, 'HEAD')[0]
    server = resp.get('server', 'N/A').strip()
    powered_by = resp.get('x-powered-by', 'N/A').strip()

    if 'apache' in server.lower():
        apache += 1

    if 'iis' in server.lower():
        iis += 1

    if 'lotus-domino' in server.lower():
        lotus += 1

    if 'sun-one' in server.lower():
        sun += 1

    if server == 'N/A':
        na += 1

    print "%s, %s" % (state, server)

    servers[server] = servers.get(server, 0) + 1
    powereds[powered_by] = powereds.get(powered_by, 0) + 1

print "State legislative server breakdown (total: %d):" % len(urls)
for server, count in servers.items():
    print "%s: %d" % (server, count)

print "\nIIS: %d\nApache: %d\nLotus-Domino: %d\nSun-ONE: %d\nN/A: %d" % (
    iis, apache, lotus, sun, na)

print "\nState 'powered-by' breakdown:"
for powered, count in powereds.items():
    print "%s: %d" % (powered, count)
