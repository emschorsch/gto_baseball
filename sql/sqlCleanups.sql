--Restrict to regular season games in 2013
select count(*) from Games where gameName LIKE '____2013%' AND type='R';

--count up games per season
select year, count(*) from game_types where game_type = 'R' GROUP BY Year;


--#create game_types1a
create table game_types1a as  select substr(e.game_id,4,4) as Year, 
    substr(e.game_id,8,4) as Date, e.game_id from games e;

--#Query to get the types of each game
create table game_types as  select g.Year, g.Date, g.game_id  , (case  when g.year = 2014 and g.date < 0930 then 'R'  when g.year = 2013 and g.date < 1002 then 'R'  when g.year = 2012 and g.date < 1005 then 'R'  when g.year = 2011 and g.date < 0929 then 'R'  when g.year = 2010 and g.date < 1004 then 'R'   when g.year = 2009 and g.date < 1007 then 'R'   when g.year = 2008 and g.date < 1001 then 'R'   when g.year = 2007 and g.date < 1002 then 'R'  when g.year = 2006 and g.date < 1002 then 'R'     when g.year = 2005 and g.date < 1003 then 'R'       when g.year = 2004 and g.date < 1004 then 'R'   when g.year = 2003 and g.date < 0929 then 'R'   when g.year = 2002 and g.date < 0930 then 'R'     when g.year = 2001 and g.date < 1008 then 'R'       when g.year = 2000 and g.date < 1002 then 'R' when g.year = 1999 and g.date < 1005 then 'R' when g.year = 1998 and g.date < 0929 then 'R' when g.year = 1997 and g.date < 0929 then 'R' when g.year = 1996 and g.date < 1001 then 'R' when g.year = 1995 and g.date < 1003 then 'R' when g.year = 1994 and g.date < 0812 then 'R' when g.year = 1993 and g.date < 1004 then 'R' when g.year = 1992 and g.date < 1005 then 'R' when g.year = 1991 and g.date < 1007 then 'R' when g.year = 1990 and g.date < 1004 then 'R' when g.year = 1989 and g.date <  1002 then 'R' when g.year = 1988 and g.date < 1003 then 'R' when g.year = 1987 and g.date < 1005 then 'R' when g.year = 1986 and g.date < 1006 then 'R' when g.year = 1985 and g.date < 1007 then 'R' when g.year = 1984 and g.date < 1001 then 'R' when g.year = 1983 and g.date < 1003 then 'R' when g.year = 1982 and g.date < 1004 then 'R' when g.year = 1981 and g.date < 1004 then 'R' when g.year = 1980 and g.date < 1007 then 'R'  when g.year = 1979 and g.date < 1001 then 'R' when g.year = 1978 and g.date < 1003 then 'R' when g.year = 1977 and g.date < 1003 then 'R' when g.year = 1976 and g.date < 1008 then 'R' when g.year = 1975 and g.date < 1003 then 'R' when g.year = 1974 and g.date < 1004 then 'R' when g.year = 1973 and g.date < 1001 then 'R' when g.year = 1972 and g.date < 1006 then 'R' when g.year = 1971 and g.date < 1001 then 'R' when g.year = 1970 and g.date < 1002 then 'R'  when g.year = 1969 and g.date < 1003 then 'R' when g.year = 1968 and g.date < 1001 then 'R' when g.year = 1967 and g.date < 1003 then 'R' when g.year = 1966 and g.date < 1004 then 'R' when g.year = 1965 and g.date < 1005 then 'R' when g.year = 1964 and g.date < 1005 then 'R' when g.year = 1963 and g.date < 1001 then 'R' when g.year = 1962 and g.date < 1001 then 'R' when g.year = 1961 and g.date < 1003 then 'R' when g.year = 1960 and g.date < 1004 then 'R'  when g.year = 1959 and g.date < 0930 then 'R' when g.year = 1958 and g.date < 0929 then 'R' when g.year = 1957 and g.date < 1001 then 'R' when g.year = 1956 and g.date < 1001 then 'R' when g.year = 1955 and g.date < 0927 then 'R' when g.year = 1954 and g.date < 0928 then 'R' when g.year = 1953 and g.date < 0929 then 'R' when g.year = 1952 and g.date < 0929 then 'R' when g.year = 1951 and g.date < 1004 then 'R' when g.year = 1950 and g.date < 1002 then 'R'  else 'P' end )
 as game_type from game_types1a g;


--For the gameday database
--#create game_types1a
create table game_types1a as  select substr(e.gameName,5,4) as Year, concat(substr(e.gameName,10,2), substr(e.gameName,13,2)) as Date, e.gameName from Games e;


--Add pitcher id to pitches table
ALTER TABLE pitches ADD pitcher_id mediumint(6) unsigned;
ALTER TABLE pitches ADD batter_id mediumint(6) unsigned;

UPDATE pitches a 
    JOIN atbats b ON a.gameAtBatId = b.num
    SET a.pitcher_id = b.pitcher;


--delete non-regular season games
--http://www4.stat.ncsu.edu/~post/sports/umpire/MLBGetData.r
delete FROM players
    WHERE gameName IN
        (SELECT gameName
        FROM Games
        WHERE Games.type = 'S');

--create new table with pitcher and batter ids
CREATE TABLE pitches2 AS 
  (SELECT pitches.*, 
          atbats.pitcher,
          atbats.batter
   FROM   pitches 
          INNER JOIN atbats 
                  ON pitches.gameAtBatID = atbats.num AND pitches.gameName = atbats.gameName);

--create new table with pitcher and batter ids
UPDATE pitches a
INNER JOIN atbats b ON
   a.gameAtBatID = b.num
SET a.pitcher_id = b.pitcher;

--add year id
ALTER TABLE Games ADD year_id mediumint(6) unsigned;
UPDATE Games SET year_id = CAST(substr(gameName,5,4) AS UNSIGNED);

--add year id
ALTER TABLE games ADD year_id mediumint(6) unsigned;
UPDATE games SET YEAR_ID = CAST(substr(game_ID,4,4) AS UNSIGNED);

--also add to events
ALTER TABLE events ADD year_id mediumint(6) unsigned;
UPDATE events SET YEAR_ID = CAST(substr(game_ID,4,4) AS UNSIGNED);

select a.game_id, a.game_type from games g 
    JOIN game_types a
    ON a.game_id = g.game_id
    where year_id = 2003 AND (AWAY_TEAM_ID = 'ATL' OR HOME_TEAM_ID = 'ATL') AND game_type = 'R' limit 4;

select
HOME_LINEUP1_BAT_ID,
HOME_LINEUP2_BAT_ID,
HOME_LINEUP3_BAT_ID,
HOME_LINEUP4_BAT_ID,
HOME_LINEUP5_BAT_ID,
HOME_LINEUP6_BAT_ID,
HOME_LINEUP7_BAT_ID,
HOME_LINEUP8_BAT_ID,
HOME_LINEUP9_BAT_ID
from games where game_id = 'ATL200303310';

CREATE TEMPORARY TABLE IF NOT EXISTS table2 AS 
    (SELECT events.BATTEDBALL_cd, events.ab_fl, events.sf_fl, events.event_cd, events.game_id, events.BAT_DEST_ID, events.BAT_TEAM_ID FROM events
         INNER JOIN game_types ON game_types.game_id = events.game_id
         where bat_id = 'jonec004' AND game_types.game_type='R' AND
              events.game_id LIKE '___2001%');

select count(*) from events where game_id LIKE BAT_ID = 'jonec004' and event_cd IN (23);


--select games in 30 day window
select game_dt, game_dt - INTERVAL 30 DAY 
from games 
WHERE (game_dt - INTERVAL 30 DAY) BETWEEN CAST('20070304' AS DATE) AND CAST('20070404' AS DATE) limit 6;


--create id_map table
CREATE TABLE id_map_full ( last varchar(12) ,first varchar(12) ,id varchar(12) ,davenport_id varchar(12) ,mlb_id varchar(12) ,retrosheet_id varchar(12) );

--add in player id_map
load data local infile 'playerid_prospectus_retrosheet_list.csv' into table id_map_full fields terminated by ','
enclosed by '"'
lines terminated by '\n'
IGNORE 1 LINES
(last, first, id, davenport_id, mlb_id, retrosheet_id);

--and to id_map_full
CREATE INDEX retrosheet_full_index ON id_map_full(retrosheet_id);

-- add debut years in id_map
CREATE TABLE id_map 
select id_map_full.*, min(year_id) AS earliest_seen,
 max(year_id) AS latest_seen
from events JOIN id_map_full ON bat_id=retrosheet_id group by bat_id

UNION

select id_map_full.*, min(year_id) AS earliest_seen,
 max(year_id) AS latest_seen
from events JOIN id_map_full ON pit_id=retrosheet_id group by pit_id

UNION

select id_map_full.*, min(year_id) AS earliest_seen,
 max(year_id) AS latest_seen
from events JOIN id_map_full ON base1_run_id=retrosheet_id group by base1_run_id

UNION

select id_map_full.*, min(year_id) AS earliest_seen,
 max(year_id) AS latest_seen
from events JOIN id_map_full ON base2_run_id=retrosheet_id group by base2_run_id

UNION

select id_map_full.*, min(year_id) AS earliest_seen,
 max(year_id) AS latest_seen
from events JOIN id_map_full ON base3_run_id=retrosheet_id group by base3_run_id;

--Find handedness of batter
ALTER TABLE id_map ADD BAT_HAND_CD VARCHAR(1);

UPDATE 
    id_map inner join
(
    select bat_id, if(count(distinct(bat_hand_cd)) = 2, 'S', if(bat_hand_cd='L', 'L', 'R')) AS handedness
from events group by bat_id
) AS t
ON id_map.retrosheet_id = t.bat_id
SET id_map.BAT_HAND_CD = t.handedness;


--Find handedness of pitcher
ALTER TABLE id_map ADD PIT_HAND_CD VARCHAR(1);

UPDATE id_map inner join
(
    select pit_id, if(count(distinct(pit_hand_cd)) = 2, 'S', if(pit_hand_cd='L', 'L', 'R')) AS handedness
from events group by pit_id
) t
ON id_map.retrosheet_id = t.pit_id
SET id_map.PIT_HAND_CD = t.handedness;

--remove duplicate rows from id_map
DELETE dupes
FROM        id_map dupes,
            id_map fullTable
WHERE       dupes.mlb_id        = fullTable.mlb_id
AND         dupes.retrosheet_id  = fullTable.retrosheet_id 
AND         (dupes.latest_seen     < fullTable.latest_seen
            OR dupes.earliest_seen > fullTable.earliest_seen)

--add index on retrosheet_id and mlb_id
CREATE INDEX retrosheet_index ON id_map(retrosheet_id);
CREATE INDEX mlb_index ON id_map(mlb_id);


-- atbat index in gameday
create index atbatIndex on atbats (gameName, num, pitcher, batter);

--show indexes
SELECT TABLE_NAME, INDEX_NAME, index_type, column_name, cardinality 
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'retrosheet';

--mysql infers Decimal(m, d) FROM 1.00000 so it determines the maximum
--precision of the similarity column
CREATE TABLE pitcher_similarity (PRIMARY KEY (pit1, pit2))
select pit1, pit2, 1.00000 AS similarity
FROM (select distinct(pit_id) AS pit1 FROM events) AS e JOIN 
    (select distinct(pit_id) AS pit2 FROM events) AS e2;

--create retrosheet_subset
mysqldump -u root retrosheet | mysql -u root retrosheet_subset
mysqldbcopy --source=root:root@localhost --destination=root:root@localhost retrosheet:retrosheet_subset
create database retrosheet_subset;
use retrosheet_subset
delete from games where year_id not in (2012, 2013, 2014);
delete from games where !(game_dt % 31 = 0 and game_dt % 3 = 0);
select year_id, count(*) from games group by year_id;
delete from events where game_id not in (select game_id from games);
delete from game_types where game_id not in (select game_id from games);
delete from comments where game_id not in (select game_id from games);
delete table id_map;
--then recreate id_map with query above
drop table pitcher_similarity
--then recreate the pitcher similarity table
OPTIMIZE Table events; --likewise for all modified tables
mysqldump -u root --databases retrosheet_subset > subset.sql

---Zack's queries for Park Factors
-- add bat_team to gameday.atbats
alter table atbats add bat_team varchar(3);
update atbats SET bat_team = if(halfinning='top', upper(left(right(atbats.gameName,15),3)),upper(left(right(atbats.gameName,8),3)));

-- add retro_game_id to gameday.Games
-- NOTE: leads to issues when gameDetail.double_header_sw is NULL
alter table Games add retro_game_id varchar(12);
update Games 
JOIN gameDetail using(gameName)
SET retro_game_id = if(double_header_sw='N', 
						concat(upper(left(right(gameName,8),3)),right(left(gameName,8),4),right(left(gameName,11),2),right(left(gameName,14),2), right(gameName,1)-1), 
						concat(upper(left(right(gameName,8),3)),right(left(gameName,8),4),right(left(gameName,11),2),right(left(gameName,14),2), right(gameName,1))
					);

-- add column <local_start_time> in gameday.Games
-- correct bug in gameday.Games.local_game_time for some doubleheaders
-- must have added retro_game_id to gameday.Games
-- NOTE: some games have local_start_time=NULL. This is likely becuase of issues with retro_game_id

alter table Games add local_start_time TIME;
update Games
JOIN retrosheet.games as r ON Games.retro_game_id=r.game_id
SET local_start_time = if(local_game_time != TIME(033300), local_game_time, if(DAYNIGHT_PARK_CD='D' and left(start_game_tm, length(start_game_tm)-2) >= 5, TIME(100*start_game_tm), TIME(100*start_game_tm + 120000)));

-- change value of gameday.Games.local_game_time when local_game_time=03:33:00
-- replaces value with start time obtained from retrosheets
update Games
JOIN retrosheet.games as r ON Games.retro_game_id=r.game_id
SET local_game_time = if(DAYNIGHT_PARK_CD='D' and left(start_game_tm, length(start_game_tm)-2) >= 5, TIME(100*start_game_tm), TIME(100*start_game_tm + 120000))
WHERE local_game_time = TIME(033300);

---End of park factor queries

-- add year to gameday.atbats
ALTER TABLE atbats add year_id YEAR(4);
UPDATE atbats
SET year_id = right(left(gameName, 8), 4);

-- add date to gameday.atbats
ALTER TABLE atbats add date_id VARCHAR(4);
UPDATE atbats
SET date_id = concat(right(left(gameName, 11), 2), right(left(gameName, 14), 2));

-- add date to gameday.gameDetail
ALTER TABLE gameDetail add date_id VARCHAR(4);
UPDATE gameDetail
SET date_id = concat(right(left(gameName, 11), 2), right(left(gameName, 14), 2));

-- add day/night flag to gameday.gameDetail
ALTER TABLE gameDetail ADD COLUMN game_time CHAR(1);
UPDATE gameDetail
SET game_time = if(5 <= HOUR(TIME(home_time)) AND HOUR(TIME(home_time)) < 12 AND home_ampm='PM', 'N', 'D');

create table park_factors (stadium CHAR(3), bat_type CHAR(1), bat_hand CHAR(1), game_time CHAR(1), num_pas MEDIUMINT(4),  
    outcome VARCHAR(9), pf DOUBLE, year_id YEAR(4), 
    PRIMARY KEY (stadium, bat_type, bat_hand, game_time, outcome, year_id)
);

LOAD DATA LOCAL INFILE 'park_factors.csv' INTO TABLE park_factors FIELDS TERMINATED BY ','  ENCLOSED BY '"'  LINES TERMINATED BY '\r\n' IGNORE 1 LINES (stadium, bat_type, bat_hand, game_time, num_pas, outcome, pf, year_id);

