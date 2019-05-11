library(DBI)
library(RMySQL)
library(fitdistrplus)

year <- ">=2012"

query <- sprintf(
"SELECT atbats.year_id, upper(home_code) as stadium,
 sum(if(event = 'Single', 1, 0))/sum(1) as single_rate,
 sum(if(event = 'Double', 1, 0))/sum(1) as double_rate,
 sum(if(event = 'Triple', 1, 0))/sum(1) as triple_rate,
 sum(if(event = 'Home Run', 1, 0))/sum(1) as hr_rate,
 sum(if(event = 'Walk', 1, 0))/sum(1) as bb_rate,
 sum(if(event in ('Strikeout', 'Strikeout - DP'), 1, 0))/sum(1) as k_rate
FROM atbats
JOIN gameDetail using(gameName)
JOIN players ON atbats.gameName=players.gameName and atbats.batter=players.id
WHERE atbats.year_id%s and ind in ('F','FR') and event!='Runner Out' and current_position!='P'
GROUP BY atbats.year_id, stadium
;", year)

gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
pf_data <- dbGetQuery(gameday, query)
dbDisconnect(gameday)

# Single season data utilized
singles.beta <- fitdist(pf_data$single_rate, "beta")
doubles.beta <- fitdist(pf_data$double_rate, "beta")
triples.beta <- fitdist(pf_data$triple_rate, "beta")
homeruns.beta <- fitdist(pf_data$hr_rate, "beta")
walks.beta <- fitdist(pf_data$bb_rate, "beta")
strikeouts.beta <- fitdist(pf_data$k_rate, "beta")

prior = data.frame(single=singles.beta[['estimate']], double=doubles.beta[['estimate']], triple=triples.beta[['estimate']], homerun=homeruns.beta[['estimate']], walk=walks.beta[['estimate']], strikeout=strikeouts.beta[['estimate']], row.names=c("alpha", "beta"))

# Plot histograms and curves
par(mfrow=c(3,2))
hist(pf_data$single_rate, prob=T, col='lightyellow', xlab="Single Rate", main=NULL)
curve(dbeta(x, prior['alpha', 'single'], prior['beta', 'single']), col='red', add=T)
hist(pf_data$double_rate, prob=T, col='lightyellow', xlab="Double Rate", main=NULL)
curve(dbeta(x, prior['alpha', 'double'], prior['beta', 'double']), col='red', add=T)
hist(pf_data$triple_rate, prob=T, col='lightyellow', xlab="Triple Rate", main=NULL)
curve(dbeta(x, prior['alpha', 'triple'], prior['beta', 'triple']), col='red', add=T)
hist(pf_data$hr_rate, prob=T, ylim=c(1,100), col='lightyellow', xlab="Home Run Rate", main=NULL)
curve(dbeta(x, prior['alpha', 'homerun'], prior['beta', 'homerun']), col='red', add=T)
hist(pf_data$bb_rate, prob=T, ylim=c(1,100), col='lightyellow', xlab="Walk Rate", main=NULL)
curve(dbeta(x, prior['alpha', 'walk'], prior['beta', 'walk']), col='red', add=T)
hist(pf_data$k_rate, prob=T, col='lightyellow', xlab="Strikeout Rate", main=NULL)
curve(dbeta(x, prior['alpha', 'strikeout'], prior['beta', 'strikeout']), col='red', add=T)
