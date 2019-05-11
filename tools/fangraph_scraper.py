import requests
import time
import re

import inspect, os
script_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory


def download_csv(link, filename):
    webpage = requests.get(link).text
    viewstate = re.findall('(?<=__VIEWSTATE\" value=\").+?(?=\" />)', webpage)[0]
    eventvalidation = re.findall('(?<=__EVENTVALIDATION\" value=\").+?(?=\" />)', webpage)[0]

    payload = {
        'RadScriptManager1_TSM': '',
        '__EVENTTARGET': 'ProjectionBoard1$cmdCSV',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': viewstate,
        '__SCROLLPOSITIONX':	360,
        '__SCROLLPOSITIONY':	343,
        '__EVENTVALIDATION': eventvalidation,
        'Header1_rdMenu_ClientState': '',
        'ProjectionBoard1_tsStats_ClientState':	{"selectedIndexes": ["0"], "logEntries": [], "scrollState": {}},
        'ProjectionBoard1_tsPosition_ClientState':	{"selectedIndexes": ["0"], "logEntries": [], "scrollState": {}},
        'ProjectionBoard1$rcbTeam':	'All Teams',
        'ProjectionBoard1_rcbTeam_ClientState': '',
        'ProjectionBoard1$rcbLeague':	'All',
        'ProjectionBoard1_rcbLeague_ClientState': '',
        'ProjectionBoard1_tsProj_ClientState':	{"selectedIndexes": [], "logEntries": [], "scrollState": {}},
        'ProjectionBoard1_tsUpdate_ClientState':	{"selectedIndexes": ["0"], "logEntries": [], "scrollState": {}},
        'ProjectionBoard1$dg1$ctl00$ctl02$ctl00$PageSizeComboBox':	30,
        'ProjectionBoard1_dg1_ctl00_ctl02_ctl00_PageSizeComboBox_ClientState': '',
        'ProjectionBoard1$dg1$ctl00$ctl03$ctl01$PageSizeComboBox':	30,
        'ProjectionBoard1_dg1_ctl00_ctl03_ctl01_PageSizeComboBox_ClientState': '',
        'ProjectionBoard1_dg1_ClientState': ''
    }
    response = requests.post(link, data=payload)

    f = open(filename, 'w')
    f.write(str(response.content))

link_dict = {"zips_ros_batters": 'http://www.fangraphs.com/projections.aspx?pos=all&stats=bat&type=rzips',
             "zips_ros_pitchers": 'http://www.fangraphs.com/projections.aspx?pos=all&stats=pit&type=rzips&team=0&lg=all&players=0',
             "zips_u_batters": 'http://www.fangraphs.com/projections.aspx?pos=all&stats=bat&type=uzips&team=0&lg=all&players=0',
             "zips_u_pitchers": 'http://www.fangraphs.com/projections.aspx?pos=all&stats=pit&type=uzips&team=0&lg=all&players=0',
             "steamer_ros_batters": 'http://www.fangraphs.com/projections.aspx?pos=all&stats=bat&type=steamerr&team=0&lg=all&players=0',
             "steamer_ros_pitchers": 'http://www.fangraphs.com/projections.aspx?pos=all&stats=pit&type=steamerr&team=0&lg=all&players=0',
             "steamer_u_batters": 'http://www.fangraphs.com/projections.aspx?pos=all&stats=bat&type=steameru&team=0&lg=all&players=0',
             "steamer_u_pitchers": 'http://www.fangraphs.com/projections.aspx?pos=all&stats=pit&type=steameru&team=0&lg=all&players=0'}


def scrape_links(link_dict):
    for link in link_dict:
        # dd/mm/yyyy format
        date = (time.strftime("%m.%d.%Y"))

        filename = script_dir + "/archives/" + link + date + ".csv"
        download_csv(link_dict[link], filename)

        time.sleep(5)

scrape_links(link_dict)
