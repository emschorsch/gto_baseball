# Calculate cFIP using gameday database

library(lme4)
library(DBI)
library(RMySQL)

year = "=2015"

query <- sprintf(
"SELECT batter, pitcher, umpires.name as umpire,
 if(halfinning='top', 'A', 'H') as team_type,
 stand as bat_hand, p_throws as pit_hand, upper(gameDetail.home_code) as stadium,
 if(event = 'Home Run', 1, 0) as HR,
 if(event in ('Strikeout', 'Strikeout - DP'), 1, 0) as K,
 if(event = 'Walk', 1, 0) as BB,
 if(event = 'Hit By Pitch', 1, 0) as HBP,
 event, gameDetail.year_id as 'year' 
FROM atbats 
JOIN umpires using(gameName) 
JOIN gameDetail using(gameName) 
WHERE umpires.position='home' and gameDetail.year_id%s and
 event != 'Runner Out' and gameDetail.ind in ('F', 'FR');", year)

gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
cfip_data <- dbGetQuery(gameday, query)

# Create data.frame of innings pitched
ip_query <- sprintf("SELECT id as pitcher, sum(outs)/3 as ip FROM pitchers WHERE year_id%s GROUP BY id;", year)
ip_data <- dbGetQuery(gameday, ip_query)
dbDisconnect(gameday)
rownames(ip_data) <- ip_data$pitcher
ip_data$pitcher <- NULL

HR <- glmer(HR ~ team_type + bat_hand*pit_hand + stadium + (1|batter) + (1|pitcher), data=cfip_data, family=binomial(link='probit'), nAGQ=0)
BB <- glmer(BB ~ team_type + bat_hand*pit_hand + stadium + (1|batter) + (1|pitcher), data=cfip_data, family=binomial(link='probit'), nAGQ=0)
HBP <- glmer(HBP ~ team_type + bat_hand*pit_hand + stadium + (1|batter) + (1|pitcher), data=cfip_data, family=binomial(link='probit'), nAGQ=0)
K <- glmer(K ~ team_type + bat_hand*pit_hand + stadium + (1|batter) + (1|pitcher), data=cfip_data, family=binomial(link='probit'), nAGQ=0)

# We want the value a pitcher provides preventing hr, bb, hbp, and k
# compared with a league average pitcher.

# HR
HR_fip <- as.data.frame(predict(HR, type="response") - predict(HR, re.form= ~(1|batter), type="response"))
colnames(HR_fip) <- 'diff'
HR_fip['pitcher'] <- cfip_data$pitcher
HR_fip <- aggregate(diff ~ pitcher, HR_fip, sum)
rownames(HR_fip) <- HR_fip$pitcher
HR_fip$pitcher <- NULL
HR_fip <- merge(HR_fip, ip_data, by='row.names')
HR_fip['rate'] <- HR_fip['diff']/HR_fip['ip']
rownames(HR_fip) <- HR_fip$Row.names
HR_fip$Row.names <- NULL

# BB
BB_fip <- as.data.frame(predict(BB, type="response") - predict(BB, re.form= ~(1|batter), type="response"))
colnames(BB_fip) <- 'diff'
BB_fip['pitcher'] <- cfip_data$pitcher
BB_fip <- aggregate(diff ~ pitcher, BB_fip, sum)
rownames(BB_fip) <- BB_fip$pitcher
BB_fip$pitcher <- NULL
BB_fip <- merge(BB_fip, ip_data, by='row.names')
BB_fip['rate'] <- BB_fip['diff']/BB_fip['ip']
rownames(BB_fip) <- BB_fip$Row.names
BB_fip$Row.names <- NULL

# HBP
HBP_fip <- as.data.frame(predict(HBP, type="response") - predict(HBP, re.form= ~(1|batter), type="response"))
colnames(HBP_fip) <- 'diff'
HBP_fip['pitcher'] <- cfip_data$pitcher
HBP_fip <- aggregate(diff ~ pitcher, HBP_fip, sum)
rownames(HBP_fip) <- HBP_fip$pitcher
HBP_fip$pitcher <- NULL
HBP_fip <- merge(HBP_fip, ip_data, by='row.names')
HBP_fip['rate'] <- HBP_fip['diff']/HBP_fip['ip']
rownames(HBP_fip) <- HBP_fip$Row.names
HBP_fip$Row.names <- NULL

# K
K_fip <- as.data.frame(predict(K, type="response") - predict(K, re.form= ~(1|batter), type="response"))
colnames(K_fip) <- 'diff'
K_fip['pitcher'] <- cfip_data$pitcher
K_fip <- aggregate(diff ~ pitcher, K_fip, sum)
rownames(K_fip) <- K_fip$pitcher
K_fip$pitcher <- NULL
K_fip <- merge(K_fip, ip_data, by='row.names')
K_fip['rate'] <- K_fip['diff']/K_fip['ip']
rownames(K_fip) <- K_fip$Row.names
K_fip$Row.names <- NULL

# Remove pitchers with 0 IP from sample
HR_fip <- HR_fip[-which(HR_fip$ip==0), ]
BB_fip <- BB_fip[-which(BB_fip$ip==0), ]
HBP_fip <- HBP_fip[-which(HBP_fip$ip==0), ]
K_fip <- K_fip[-which(K_fip$ip==0), ]

# Remove pitchers with < 20 IP from sample
#HR_fip <- HR_fip[-which(HR_fip$ip<20), ]
#BB_fip <- BB_fip[-which(BB_fip$ip<20), ]
#HBP_fip <- HBP_fip[-which(HBP_fip$ip<20), ]
#K_fip <- K_fip[-which(K_fip$ip<20), ]

# Compute cfip differential
cfip <- 13*HR_fip['rate'] + 3*(BB_fip['rate']+HBP_fip['rate']) - 2*(K_fip['rate'])

# z-transforms cfip to N(0,1)
cfip <- (cfip-mean(cfip$rate))/sd(cfip$rate)

# z-transforms cfip to N(100,15^2)
cfip <- 15*cfip+100

# Order cfip ascending
colnames(cfip) <- "cfip"
cfip['pitcher'] <- rownames(cfip)
cfip['year_id'] <- as.integer(substr(year, 2, 5))
cfip <- cfip[c("pitcher", "cfip", "year_id")]
cfip <- cfip[order(cfip$cfip), ]
head(cfip, 10)

# Append to gameday.cfip table
# gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
# dbWriteTable(gameday, "cfip", cfip, append=TRUE, row.names=FALSE, field.type=list(pitcher="MEDIUMINT(6)", cfip="DOUBLE", year_id="YEAR(4)"))
# dbDisconnect(gameday)

# Overwrite gameday.cfip table
# gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
# dbWriteTable(gameday, "cfip", cfip, overwrite=TRUE, row.names=FALSE, field.type=list(pitcher="MEDIUMINT(6)", cfip="DOUBLE", year_id="YEAR(4)"))
# dbDisconnect(gameday)

# Create new gameday.cfip table
# gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
# dbWriteTable(gameday, "cfip", cfip, row.names=FALSE, field.type=list(pitcher="MEDIUMINT(6)", cfip="DOUBLE", year_id="YEAR(4)"))
# dbDisconnect(gameday)