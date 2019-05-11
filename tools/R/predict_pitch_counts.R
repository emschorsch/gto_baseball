library(DBI)
library(RMySQL)
library(dplyr)

starts_query <- (
"SELECT name, id, avg(pitches) as pitches, cfip, year_id FROM (
SELECT pitchers.id, pitchers.name_display_first_last as name, pitchers.outs, pitchers.bf,
 pitchers.er, pitchers.r, pitchers.h, pitchers.hr, pitchers.bb, pitchers.so, pitchers.win,
 pitchers.loss, pitchers.note, pitchers.year_id, sum(1) as pitches, cfip.cfip 
FROM pitchers 
JOIN pitches ON pitches.pitcher=pitchers.id and pitches.gameName=pitchers.gameName 
JOIN players ON players.gameName=pitchers.gameName and players.id=pitchers.id 
JOIN cfip ON cfip.pitcher=pitchers.id and cfip.year_id=pitchers.year_id 
WHERE players.game_position='P' and pitchers.gameName!='gid_2014_03_23_lanmlb_arimlb_1' 
GROUP BY pitchers.gameName, pitchers.id) a 
GROUP BY id, year_id
HAVING count(*)>=10;")

gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
starts <- dbGetQuery(gameday, starts_query)
dbDisconnect(gameday)
head(starts)
hist(starts$pitches, breaks=seq(0, 150, 1), prob=TRUE)

pred <- merge(merge(filter(starts, year_id==2012), filter(starts, year_id==2013)[c("id", "pitches")], by='id'), merge(filter(starts, year_id==2013), filter(starts, year_id==2014)[c("id", "pitches")], by='id'), all=TRUE)
colnames(pred) <- c("id", "name", "year_pitches", "cfip", "year_id", "pred_pitches")

# We see that pitchers with cFIP < 80 throw more pitches per start than other pitchers.
# We see that pitchers who throw > 105 pitches per start the previous year throw
#     more pitches per start the following season.
# Pitches per start the previous year has a higher correlation and F-statistic when
#     predicting the following year's pitches per start.
# Combining previous year's pitches with cFIP to create a multivariate linear model
#     does not significantly improve predictions.
plot(pred$year_pitches, pred$pred_pitches, xlab="year N pitches", ylab='year N+1 pitches')
# Adjusted R^2 = 0.2896
abline(lm(pred_pitches ~ year_pitches, pred), col='red')
plot(pred$cfip, pred$pred_pitches, xlab="cFIP", ylab='year N+1 pitches')
# Adjusted R^2 = 0.1716
abline(lm(pred_pitches ~ cfip, pred), col='red')

# Examing the season after a pitcher throws > 105 pitches per start.
# The sample is too small to draw strong conclusions.
# We don't find strong evidence that modelling future pitches per start is preferred to
#     setting this entire group = 105 pitches per start the following season.
# We, therefore, set these pitches expected pitches per start = 105 for all pitchers the following season
high_ip <- filter(pred, year_pitches>105)
yearN_model <- lm(pred_pitches ~ year_pitches, high_ip)
cfip_model <- lm(pred_pitches ~ cfip, high_ip)
multi_model <- lm(pred_pitches ~ year_pitches + cfip, high_ip)
high_ip['yearN_pred'] <- predict(yearN_model, type='response')
high_ip['cfip_pred'] <- predict(cfip_model, type='response')
high_ip['multi_model'] <- predict(multi_model, type='response')

# TODO: Perform further analysis how to treat rookies.
#       Do rookies require further adjustment or is lesser average pitches per start due to
#           a mix of inferior pitches and manager's decisions to limit pitches, which
#           need to be handled on a case-by-case basis?

# Selects starts by rookies in 2013 and 2014
rookie_starts_query <- (
  "SELECT pitchers.*, sum(1) as pitches, cfip
  FROM pitchers
  JOIN pitches ON pitches.pitcher=pitchers.id and pitches.gameName=pitchers.gameName
  JOIN players ON players.gameName=pitchers.gameName and players.id=pitchers.id
  JOIN cfip ON cfip.pitcher=pitchers.id and cfip.year_id=pitchers.year_id
  JOIN (select mlb_id, min(earliest_seen) as earliest_seen from retrosheet.id_map GROUP BY mlb_id) as r on pitchers.id=r.mlb_id and pitchers.year_id=r.earliest_seen  # Limit to rookies
  WHERE players.game_position='P' and pitchers.gameName!='gid_2014_03_23_lanmlb_arimlb_1' and r.earliest_seen>2012
  GROUP BY gameName, id;")

gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
rookie_starts <- dbGetQuery(gameday, rookie_starts_query)
dbDisconnect(gameday)
head(rookie_starts)
hist(rookie_starts$pitches, breaks=seq(0, 150, 1), prob=TRUE)


# Non-Rookie pitchers do not show significant differences from the overall basket that
#     includes both rookies and non-rookies.
# This is likely due to the proportion of starts by rookies.

#Non-rookies in 2013, 2014
non_rookie_starts_query <- (
  "SELECT pitchers.*, sum(1) as pitches, cfip
  FROM pitchers
  JOIN pitches ON pitches.pitcher=pitchers.id and pitches.gameName=pitchers.gameName
  JOIN players ON players.gameName=pitchers.gameName and players.id=pitchers.id
  JOIN cfip ON cfip.pitcher=pitchers.id and cfip.year_id=pitchers.year_id
  JOIN (select mlb_id, min(earliest_seen) as earliest_seen from retrosheet.id_map GROUP BY mlb_id) as r on pitchers.id=r.mlb_id  and r.earliest_seen!=pitchers.year_id  # Limit to non-rookies
  WHERE players.game_position='P' and pitchers.gameName!='gid_2014_03_23_lanmlb_arimlb_1'
  GROUP BY gameName, id;")

gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
non_rookie_starts <- dbGetQuery(gameday, non_rookie_starts_query)
dbDisconnect(gameday)
head(non_rookie_starts)
hist(non_rookie_starts$pitches, breaks=seq(0, 150, 1), prob=TRUE)