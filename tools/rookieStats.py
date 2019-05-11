
#!/usr/bin/python
from __future__ import print_function

import MySQLdb
import numpy as np


db = MySQLdb.connect(host="localhost",  # your host, usually localhost
                             user="bbos",       # your username
                             passwd="bbos",     # your password
                             db="retrosheet")   # name of the data base

# you must create a Cursor object. It will let
#  you execute all the queries you need
cur = db.cursor()

base_query = """CREATE TEMPORARY TABLE IF NOT EXISTS table2 AS(
    SELECT PIT_ID, mlb_id, e.BAT_ID, e.BATTEDBALL_cd, e.ab_fl, e.sf_fl, e.event_cd, e.game_id, e.BAT_DEST_ID, e.BAT_TEAM_ID
    FROM (events e JOIN game_types Using(game_id)) JOIN id_map
    ON e.BAT_ID = retrosheet_id
    WHERE game_types.game_type='R' AND e.YEAR_ID>=2012
        AND e.YEAR_ID = earliest_seen );"""
cur.execute(base_query)

query = """SELECT event_cd, COUNT(*)
    FROM table2
    WHERE event_cd IN (3,14,15,16,20,21,22,23)
    GROUP BY event_cd;"""
cur.execute(query)
results = dict(cur.fetchall())

cur.execute("SELECT count(*) from table2 WHERE AB_FL ='T';")
ab = cur.fetchall()
results['ab'] = int(ab[0][0])

hr, tr, db, single = results[23], results[22], results[21], results[20]
ab, so = results['ab'], results[3]
outs = ab - hr - tr - db - single - so
walks = results[14] + results[15]
stats = [hr, tr, db, single, walks, so, outs]
# TODO: does this makes sense? Should we be normalizing by PA?
print( stats)

