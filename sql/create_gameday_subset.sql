CREATE DATABASE gameday_subset;
use gameday_subset;

create table Games LIKE gameday.Games; Insert  Games  select * from gameday.Games 
WHERE year_id IN (2012, 2013, 2014) AND type='R';

create table Stadiums LIKE gameday.Stadiums; Insert Stadiums select Stadiums.* from gameday.Stadiums JOIN Games USING(gameName);
create table Teams LIKE gameday.Teams; Insert Teams   select Teams.* from gameday.Teams JOIN Games USING(gameName);
create table action LIKE gameday.action; Insert  action  select action.* from gameday.action JOIN Games USING(gameName);
create table atbats LIKE gameday.atbats; Insert atbats   select atbats.* from gameday.atbats JOIN Games USING(gameName);
create table batters LIKE gameday.batters; Insert batters   select batters.* from gameday.batters JOIN Games USING(gameName);
create table coaches LIKE gameday.coaches; Insert  coaches  select coaches.* from gameday.coaches JOIN Games USING(gameName);
create table feedPlays LIKE gameday.feedPlays; Insert  feedPlays  select feedPlays.* from gameday.feedPlays JOIN Games USING(gameName);
create table gameConditions LIKE gameday.gameConditions; Insert gameConditions   select gameConditions.* from gameday.gameConditions JOIN Games USING(gameName);
create table gameDetail LIKE gameday.gameDetail; Insert  gameDetail  select gameDetail.* from gameday.gameDetail JOIN Games USING(gameName);
create table hits LIKE gameday.hits;  Insert hits    select hits.* from gameday.hits JOIN Games USING(gameName);
create table pitchers LIKE gameday.pitchers; Insert pitchers   select pitchers.* from gameday.pitchers JOIN Games USING(gameName);
create table pitches LIKE gameday.pitches; Insert pitches   select pitches.* from gameday.pitches JOIN Games USING(gameName);
create table playerBIOs LIKE gameday.playerBIOs;  Insert playerBIOs    select playerBIOs.* from gameday.playerBIOs JOIN Games USING(gameName);
create table players LIKE gameday.players; Insert players   select players.* from gameday.players JOIN Games USING(gameName);
create table pregumboHits LIKE gameday.pregumboHits; Insert pregumboHits   select pregumboHits.* from gameday.pregumboHits JOIN Games USING(gameName);
create table runners LIKE gameday.runners; Insert runners   select runners.* from gameday.runners JOIN Games USING(gameName);
create table teamNames LIKE gameday.teamNames; Insert teamNames   select teamNames.* from gameday.teamNames JOIN Games USING(gameName);
create table umpires LIKE gameday.umpires; Insert umpires   select umpires.* from gameday.umpires JOIN Games USING(gameName);
