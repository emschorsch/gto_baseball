-- add bat_team to gameday.atbats
alter table atbats add bat_team varchar(3);
update atbats SET bat_team = if(halfinning='top', upper(left(right(atbats.gameName,15),3)),upper(left(right(atbats.gameName,8),3)));

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

-- raname 'year' column 'year_id' in gameday.Games
ALTER TABLE gameDetail CHANGE year year_id YEAR(4);

-- add indices to gameday.atbats
ALTER TABLE `atbats` ADD INDEX `gameName` (`gameName`);
ALTER TABLE `atbats` ADD INDEX atbatsIndex (gameName, num, pitcher, batter);

-- Copy fangraphs_pf table from old gameday table
CREATE TABLE fangraphs_pf LIKE gameday_old.fangraphs_pf;
INSERT fangraphs_pf SELECT * from gameday_old.fangraphs_pf;

-- add index to gameday.gameDetail
ALTER TABLE gameDetail ADD INDEX gameName (gameName);

-- add index to gameday.Games
-- is this necessary or does Games already have a primary key?
ALTER TABLE Games ADD INDEX gameName (gameName);

-- add index to gameday.hits
ALTER TABLE hits ADD INDEX hitID (hitID);

-- Copy park_factors table from old gameday database
CREATE TABLE park_factors LIKE gameday_old.park_factors;
INSERT park_factors SELECT * from gameday_old.park_factors;

-- Copy pitcher_similarity table from old gameday database
CREATE TABLE pitcher_similarity LIKE gameday_old.pitcher_similarity;
INSERT pitcher_similarity SELECT * from gameday_old.pitcher_similarity;

-- Copy pitcher_similarity_copy table from old gameday database
CREATE TABLE pitcher_similarity_copy LIKE gameday_old.pitcher_similarity_copy;
INSERT pitcher_similarity_copy SELECT * from gameday_old.pitcher_similarity_copy;

-- copy cfip table from old gameday database
CREATE TABLE cfip LIKE gameday_old.cfip;
INSERT cfip SELECT * FROM gameday_old.cfip;

-- add column `year_id` to pitchers
ALTER TABLE pitchers ADD COLUMN year_id YEAR(4);
UPDATE pitchers SET year_id = right(left(gameName, 8), 4);

-- add indices to pitchers table
ALTER TABLE pitchers ADD INDEX year_id (year_id);
ALTER TABLE pitchers ADD INDEX id (id);

-- add indices to pitches table
ALTER TABLE pitches ADD PRIMARY KEY (gamedayPitchID);
ALTER TABLE pitches ADD INDEX pitchesIndex (gameName, gameAtBatID, gameDayPitchID);

-- add indices to players table
ALTER TABLE players ADD INDEX gameName (gameName);
ALTER TABLE players ADD INDEX id (id);

-- add indices to runners
ALTER TABLE `runners` ADD PRIMARY KEY (gamedayRunnerID);
ALTER TABLE `runners` ADD INDEX runnersIndex (gameName, gameAtBatID, gamedayRunnerID);

-- Remove duplicate boston game from database
DELETE FROM action WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM atbats WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM batters WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM coaches WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM feedPlays WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM gameConditions WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM gameDetail WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM Games WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM hits WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM pitchers WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM pitches WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM playerBIOs WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM players WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM pregumboHits WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM runners WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM Stadiums WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM teamNames WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM Teams WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';
DELETE FROM umpires WHERE gameName='gid_2012_07_21_tormlb_bosmlb_1_bak0';

-- Remove duplicates from LAN, ARI game on 03/23/14 in atbats table
DELETE FROM atbats WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1' AND away_team_runs is NULL AND home_team_runs is NULL;

-- Remove duplicates from LAN, ARI game on 03/23/14 in batters table
DELETE b1 
FROM batters b1 
JOIN batters b2 using(gameName, id) 
WHERE b1.ab < b2.ab and gameName='gid_2014_03_23_lanmlb_arimlb_1';

-- Remove duplicates from LAN, ARI game on 03/23/14 in coaches table
DELETE FROM coaches WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1' AND ((last='Stottlemyre Jr.') OR (last='Yeager' and num is NULL) OR (position='quality_assurance_coach') OR (num=12));

-- Remove duplicates from LAN, ARI game on 03/23/14 in gameCondition table
DELETE from gameConditions WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1' and attendence='';

-- Remove duplicates from LAN, ARI game on 03/23/14 in gameDetail table
DELETE from gameDetail WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1' and status!='Final';

-- Remove duplicates from LAN, ARI game on 03/23/14 in pitchers table
DELETE p1 FROM pitchers p1 
JOIN pitchers p2 USING(gameName, id) 
WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1' and p1.outs < p2.outs;

-- Remove duplicates from LAN, ARI game on 03/23/14 in pitches table
DELETE p1 FROM pitches p1 
JOIN (SELECT * from pitches WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1') p2 USING(gameName, gameAtBatID, id) 
WHERE p1.gamedayPitchId > p2.gamedayPitchID;

-- Remove duplicates from LAN, ARI game on 03/23/14 in players table
Delete FROM players 
WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1' and current_position is NULL and left(status, 1)!='D' 
and id in (SELECT id FROM (SELECT count(*), players.* FROM players WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1' GROUP BY id HAVING count(*)>1 ORDER BY id) a);
DELETE FROM players WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1' and last in ('Gordon', 'Trumbo') and position in ('2B', 'RF');

-- Remove duplicates from LAN, ARI game on 03/23/14 in runners table
DELETE FROM runners WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1' and gameDayRunnerID in (2840046, 2840049, 2840050);

-- Remove duplicates from LAN, ARI game on 03/23/14 in Teams table
DELETE FROM Teams WHERE gameName='gid_2014_03_23_lanmlb_arimlb_1' and (w=1 OR l=1);
