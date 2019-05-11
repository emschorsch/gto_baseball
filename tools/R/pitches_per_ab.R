library(DBI)
library(RMySQL)
library(dplyr)
library(fitdistrplus)

# TODO: Should intentional walks be included with walks? They are currently ignored.
pitches_query <- (
"SELECT cfip, a.pitcher,
 IF(a.outcome in ('Single', 'Double', 'Triple', 'Home Run'), 'Hit',
    IF(a.outcome in ('Strikeout', 'Strikeout - DP'), 'Strikeout',
       IF(a.outcome in ('Walk', 'Hit By Pitch'), a.outcome, 'Out'))) as outcome,
 a.pitches, year_id 
FROM (
SELECT atbats.gameName as 'game', atbats.num as num, atbats.pitcher as pitcher,
 atbats.event as outcome, sum(1) as pitches 
FROM atbats 
JOIN pitches ON pitches.gameName=atbats.gameName and pitches.gameAtBatID=atbats.num 
WHERE atbats.event NOT in ('Runner Out', 'Intent Walk') 
GROUP BY game, num
) a
JOIN cfip ON cfip.pitcher=a.pitcher and cfip.year_id=right(left(game,8),4) 
ORDER BY pitches DESC;")

gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
pitches <- dbGetQuery(gameday, pitches_query)
dbDisconnect(gameday)
head(pitches)

# All pitchers
par(mfrow=c(2,2))
hist(filter(pitches, outcome=='Hit')$pitches, breaks=seq(1,20,1), prob=T, main=NULL, xlab='Pitcher per Hit')
hist(filter(pitches, outcome=='Out')$pitches, breaks=seq(1,20,1), prob=T, main=NULL, xlab='Pitcher per Out')
hist(filter(pitches, outcome=='Strikeout')$pitches, breaks=seq(1,20,1), prob=T, main=NULL, xlab='Pitcher per K')
hist(filter(pitches, outcome=='Walk')$pitches, breaks=seq(1,20,1), prob=T, main=NULL, xlab='Pitcher per Walk')

# All pitchers
# We graph scatter plots of Pitchers/Outcome against cFIP.
# Overall we see very little correlation between cFIP and Pitches/Outcome.
# We see the strongest correlation bewtween cFIP and Pitches/Walk.
# We don't think the difference in expected pitches is significant enough
# to differ expected pitches/outcome in the simulator based on cFIP.
par(mfrow=c(2,2))
plot(filter(pitches, outcome=='Walk')$cfip, filter(pitches, outcome=='Walk')$pitches, ylab='Pitches per Walk', xlab='cFIP')
abline(lm(filter(pitches, outcome=='Walk')$pitches ~ filter(pitches, outcome=='Walk')$pitches), col='red')
plot(filter(pitches, outcome=='Strikeout')$cfip, filter(pitches, outcome=='Strikeout')$pitches, ylab='Pitches per Strikeout', xlab='cFIP')
abline(lm(filter(pitches, outcome=='Strikeout')$pitches ~ filter(pitches, outcome=='Strikeout')$cfip), col='red')
plot(filter(pitches, outcome=='Hit')$cfip, filter(pitches, outcome=='Hit')$pitches, ylab='Pitches per Hit', xlab='cFIP')
abline(lm(filter(pitches, outcome=='Hit')$pitches ~ filter(pitches, outcome=='Hit')$cfip), col='red')
plot(filter(pitches, outcome=='Out')$cfip, filter(pitches, outcome=='Out')$pitches, ylab='Pitches per Out', xlab='cFIP')
abline(lm(filter(pitches, outcome=='Out')$pitches ~ filter(pitches, outcome=='Out')$cfip), col='red')

# Histograms of pitches per hit by cfip
# We see no significant difference in histograms
par(mfrow=c(2,2))
hist(filter(pitches, outcome=='Hit', cfip<=70)$pitches, breaks=seq(1,20,1), prob=T, main='cFIP <= 70', xlab='Pitcher per Hit', col='lightyellow')
hist(filter(pitches, outcome=='Hit', cfip>70, cfip<130)$pitches, breaks=seq(1,20,1), prob=T, main='70 < cFIP < 130', xlab='Pitcher per Hit', col='lightyellow')
hist(filter(pitches, outcome=='Hit', cfip>=130)$pitches, breaks=seq(1,20,1), prob=T, main='cFIP >= 130', xlab='Pitcher per Hit', col='lightyellow')
hist(filter(pitches, outcome=='Hit')$pitches, breaks=seq(1,20,1), prob=T, main='All Pitchers', xlab='Pitcher per Hit', col='lightyellow')

# Histograms of pitches per out by cfip
# We see no significant differences in histograms
par(mfrow=c(2,2))
hist(filter(pitches, outcome=='Out', cfip<=70)$pitches, breaks=seq(1,20,1), prob=T, main='cFIP <= 70', xlab='Pitcher per Out', col='lightyellow')
hist(filter(pitches, outcome=='Out', cfip>70, cfip<130)$pitches, breaks=seq(1,20,1), prob=T, main='70 < cFIP < 130', xlab='Pitcher per Out', col='lightyellow')
hist(filter(pitches, outcome=='Out', cfip>=130)$pitches, breaks=seq(1,20,1), prob=T, main='cFIP >= 130', xlab='Pitcher per Out', col='lightyellow')
hist(filter(pitches, outcome=='Out')$pitches, breaks=seq(1,20,1), prob=T, main='All Pitchers', xlab='Pitcher per Out', col='lightyellow')

# Histograms of pitches per k by cfip
# Pitchers with cFIP < 70 are more likely to strikeout batters using 3 or 4 pitches.
# Pitcher with cFIP >=130 are more likely to strikout batters on 5 pitches.
# Striking out batters using > 5 pitches appears comparable.
par(mfrow=c(2,2))
hist(filter(pitches, outcome=='Strikeout', cfip<=70)$pitches, breaks=seq(1,20,1), prob=T, main='cFIP <= 70', xlab='Pitcher per K', col='lightyellow')
hist(filter(pitches, outcome=='Strikeout', cfip>70, cfip<130)$pitches, breaks=seq(1,20,1), prob=T, main='70 < cFIP < 130', xlab='Pitcher per K', col='lightyellow')
hist(filter(pitches, outcome=='Strikeout', cfip>=130)$pitches, breaks=seq(1,20,1), prob=T, main='cFIP >= 130', xlab='Pitcher per K', col='lightyellow')
hist(filter(pitches, outcome=='Strikeout')$pitches, breaks=seq(1,20,1), prob=T, main='All Pitchers', xlab='Pitcher per K', col='lightyellow')

# Histograms of pitches per walk by cfip
# We see the most pronounced difference here. Pitchers with cFIP<=70 are significantly less
# likely to walk batters on fewer than 6 pitches anf significantly more likely walk batters
# on greater than 6 pitches. Walks on 6 pitches are about equal.
par(mfrow=c(2,2))
hist(filter(pitches, outcome=='Walk', cfip<=70)$pitches, breaks=seq(1,20,1), prob=T, main='cFIP <= 70', xlab='Pitcher per Walk', col='lightyellow')
hist(filter(pitches, outcome=='Walk', cfip>70, cfip<130)$pitches, breaks=seq(1,20,1), prob=T, main='70 < cFIP < 130', xlab='Pitcher per Walk', col='lightyellow')
hist(filter(pitches, outcome=='Walk', cfip>=130)$pitches, breaks=seq(1,20,1), prob=T, main='cFIP >= 130', xlab='Pitcher per Walk', col='lightyellow')
hist(filter(pitches, outcome=='Walk')$pitches, breaks=seq(1,20,1), prob=T, main='All Pitchers', xlab='Pitcher per Walk', col='lightyellow')

# Create cdfs and pmfs of pitches per outcome
hit.cdf <- count(filter(pitches, outcome=='Hit'), vars=pitches)
hit.cdf['hit_prob'] <- ecdf(filter(pitches, outcome=='Hit')$pitches)(knots(ecdf(filter(pitches, outcome=='Hit')$pitches)))
hit.cdf['pmf'] <- hit.cdf['n']/sum(hit.cdf['n'])
out.cdf <- count(filter(pitches, outcome=='Out'), vars=pitches)
out.cdf['out_prob'] <- ecdf(filter(pitches, outcome=='Out')$pitches)(knots(ecdf(filter(pitches, outcome=='Out')$pitches)))
out.cdf['pmf'] <- out.cdf['n']/sum(out.cdf['n'])
k.cdf <- count(filter(pitches, outcome=='Strikeout'), vars=pitches)
k.cdf['strikeout_prob'] <- ecdf(filter(pitches, outcome=='Strikeout')$pitches)(knots(ecdf(filter(pitches, outcome=='Strikeout')$pitches)))
k.cdf['pmf'] <- k.cdf['n']/sum(k.cdf['n'])
bb.cdf <- count(filter(pitches, outcome=='Walk'), vars=pitches)
bb.cdf['walk_prob'] <- ecdf(filter(pitches, outcome=='Walk')$pitches)(knots(ecdf(filter(pitches, outcome=='Walk')$pitches)))
bb.cdf['pmf'] <- bb.cdf['n']/sum(bb.cdf['n'])
hbp.cdf <- count(filter(pitches, outcome=="Hit By Pitch"), vars=pitches)
hbp.cdf['hbp_prob'] <- ecdf(filter(pitches, outcome=='Hit By Pitch')$pitches)(knots(ecdf(filter(pitches, outcome=='Hit By Pitch')$pitches)))
hbp.cdf['pmf'] <- hbp.cdf['n']/sum(hbp.cdf['n'])
