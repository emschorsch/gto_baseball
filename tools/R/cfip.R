# This cFIP model uses the retrosheet databases. It was made to exactly duplicate the cFIP
# cFIP method described at http://www.hardballtimes.com/fip-in-context/. This model
# replicates the method described as best as possible; however, we are not able to
# precisely match the results, which are found at
# https://onedrive.live.com/view.aspx?resid=9EE1CA9222EEDD14!5531&ithint=file%2cxlsx&app=Excel&authkey=!AMFxtpKq5TpirKM

library(lme4)
library(DBI)
library(RMySQL)

year <- "=2013"

query <- sprintf(
"SELECT e.bat_id as batter, e.pit_id as pitcher, e.pos2_fld_id as catcher, g.base4_ump_id as umpire, if(e.BAT_HOME_id=1, 'H', 'A') as team_type, e.bat_hand_cd as bat_hand, e.pit_hand_cd as pit_hand, e.home_team_id as stadium, if(e.event_cd=23, 1, 0) as HR, if(e.event_cd=3, 1, 0) as K, if(e.event_cd=14, 1, 0) as BB, if(e.event_cd=16, 1, 0) as HBP, if(e.event_cd=14 or event_cd=16, 1, 0) as BB_or_HBP, SHORTNAME_TX as event, e.year_id as year
FROM events e
JOIN LKUP_CD_EVENT 
ON event_cd=value_cd
JOIN games g
using(game_id)
WHERE e.bat_event_fl='T' and e.year_id%s;", year)

retro <- dbConnect(RMySQL::MySQL(), dbname='retrosheet', user='bbos', password='bbos')
cfip_data <- dbGetQuery(retro, query)

# Create data.frame of retrosheet/mlbid id_map
id_map_query <- "select retrosheet_id, mlb_id from id_map_full group by retrosheet_id;"
id_map <- dbGetQuery(retro, id_map_query)
rownames(id_map) <- id_map$retrosheet_id
id_map <- id_map[2]

# Map pitcher retro_id to mlb_id 
cfip_data['pitcher'] <- id_map[cfip_data$pitcher, 1]
cfip_data['batter'] <- id_map[cfip_data$batter, 1]
cfip_data['catcher'] <- id_map[cfip_data$catcher, 1]

# Create data.frame of innings pitched
ip_query <- sprintf("select pit_id, sum(event_outs_ct)/3 as ip from events where year_id%s group by pit_id;", year)
ip_data <- dbGetQuery(retro, ip_query)
dbDisconnect(retro)
ip_data['pit_id'] <- id_map[ip_data$pit_id, 1]
rownames(ip_data) <- ip_data$pit_id
ip_data$pit_id <- NULL

# Run mixed models to components of FIP
HR <- glmer(HR ~ bat_hand*pit_hand + stadium + (1|batter) + (1|pitcher), data=cfip_data, family=binomial(link='probit'), nAGQ=0)
BB <- glmer(BB ~ team_type + bat_hand*pit_hand + stadium + (1|batter) + (1|pitcher) + (1|catcher) + (1|umpire), data=cfip_data, family=binomial(link='probit'), nAGQ=0)
HBP <- glmer(HBP ~ team_type + bat_hand*pit_hand + stadium + (1|batter) + (1|pitcher) + (1|catcher), data=cfip_data, family=binomial(link='probit'), nAGQ=0)
K <- glmer(K ~ team_type + bat_hand*pit_hand + stadium + (1|batter) + (1|pitcher) + (1|catcher), data=cfip_data, family=binomial(link='probit'), nAGQ=0)

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
BB_fip <- as.data.frame(predict(BB, type="response") - predict(BB, re.form= ~(1|batter)+(1|catcher)+(1|umpire), type="response"))
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
HBP_fip <- as.data.frame(predict(HBP, type="response") - predict(HBP, re.form= ~(1|batter)+(1|catcher), type="response"))
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
K_fip <- as.data.frame(predict(K, type="response") - predict(K, re.form= ~(1|batter)+(1|catcher), type="response"))
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
