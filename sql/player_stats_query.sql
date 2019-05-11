CREATE TEMPORARY TABLE IF NOT EXISTS table2 AS
(SELECT e.BAT_ID, e.BATTEDBALL_cd, e.ab_fl, e.sf_fl, e.event_cd, 
    e.game_id, e.BAT_DEST_ID, e.BAT_TEAM_ID
FROM events e
INNER JOIN game_types ON game_types.game_id = e.game_id
WHERE game_types.game_type='R'
GROUP BY e.BAT_ID

-- pivot table
SELECT  BAT_ID,
  GROUP_CONCAT(if(event_cd = 21, value, NULL)) AS 'Double',
  GROUP_CONCAT(if(event_cd = 22, value, NULL)) AS 'Triple',
  GROUP_CONCAT(if(event_cd = 23, value, NULL)) AS 'HR'
FROM
    (  )
GROUP BY BAT_ID
LIMIT 10;


DECLARE @Constant INT = 2015;

--if it's three years ago weight as 3 parts
-- two years 4 parts
-- one years 5 parts

SELECT BAT_ID, YEAR, 
    SUM(if(event_cd = 21, 1, 0)) As 'Double',
    SUM(if(event_cd = 22, 1, 0)) As 'Triple',
    SUM(if(event_cd = 23, 1, 0)) As 'HR'
  FROM events JOIN game_types USING(game_id)
  WHERE game_type='R' AND event_cd IN (21, 22, 23)
  GROUP BY BAT_ID, YEAR
  LIMIT 50;


SELECT BAT_ID, BAT_HAND_CD
, PIT_HAND_CD, YEAR_ID
, SUM(IF(EVENT_CD = "20", 1,0)) AS 1B
, SUM(IF(EVENT_CD = "21", 1,0)) AS 2B
, SUM(IF(EVENT_CD = "22", 1,0)) AS 3B
, SUM(IF(EVENT_CD = "23", 1,0)) AS HR
, SUM(IF(EVENT_CD = "14", 1,0)) AS BB
, SUM(IF(EVENT_CD = "16", 1,0)) AS HBP
, SUM(IF(EVENT_CD = "15", 1,0)) AS IBB
, SUM(IF(EVENT_CD = "3", 1,0)) AS K
, SUM(IF(DP_FL = "T",1,0)) AS DP
, SUM(IF(BAT_EVENT_FL = "T", 1,0)) AS PA
FROM retrosheet.events e
WHERE YEAR_ID > 1993
AND e.BAT_FLD_CD != "1"
GROUP BY BAT_ID, BAT_HAND_CD, PIT_HAND_CD, YEAR_ID;

--Rookie stats
CREATE TEMPORARY TABLE IF NOT EXISTS table2 AS(
    SELECT PIT_ID, mlb_id, e.BAT_ID, e.BATTEDBALL_cd, e.ab_fl, e.sf_fl, e.event_cd, e.game_id, e.BAT_DEST_ID, e.BAT_TEAM_ID 
    FROM events e 
    INNER JOIN game_types Using(game_id)
    INNER JOIN id_map 
    ON e.BAT_ID = retrosheet_id 
    WHERE game_types.game_type='R' AND e.YEAR_ID>=2012
        AND e.YEAR_ID = earliest_seen );

SELECT event_cd, COUNT(*) 
FROM table2 
WHERE event_cd IN (3,14,15,16,20,21,22,23) 
GROUP BY event_cd;

SELECT bat_id, count(*)
from table2
WHERE AB_FL = 'T';
