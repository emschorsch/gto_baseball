# Calculates Contextual Park Factors for <year>.
# Program runtime is 16 minutes for one season.
library(DBI)
library(RMySQL)
library(lme4)
library(dplyr)

setwd("~/baseball/tools/R/")
# Calculates and stores `prior` data.frame
# `prior` is calculated using data from all seasons since 2012
source("pf_priors.R", local=TRUE)

year_condition <- 2016

pf_query <- sprintf(
"SELECT pitcher, batter, bat_team,
 upper(left(right(atbats.gameName,8),3)) as stadium,
 stadiumID as stadium_id,
 if(halfinning='top', 'A', 'H') as bat_type,
 stand as bat_hand, game_time,
 if(event = 'Single', 1, 0) as single,
 if(event = 'Double', 1, 0) as 'double',
 if(event = 'Triple', 1, 0) as triple,
 if(event = 'Home Run', 1, 0) as homerun,
 if(event = 'Walk', 1, 0) as walk,
 if(event = 'Hit By Pitch', 1, 0) as hitbypitch,
 if(event = 'Intent Walk', 1, 0) as intentionalwalk,
 if(event in ('Strikeout','Strikeout - DP'), 1, 0) as strikeout,
 1 as PA 
FROM atbats 
JOIN Games using(gameName) 
JOIN gameDetail using(gameName) 
JOIN players ON atbats.gameName=players.gameName
 and atbats.batter=players.id 
JOIN park_renovations ON upper(left(right(atbats.gameName,8),3))=park_renovations.stadium 
WHERE atbats.year_id BETWEEN %s AND %s and atbats.year_id>=park_renovations.relevant_year
 and ind in ('F','FR') and event!='Runner Out' and current_position!='P'
;", year_condition-4, year_condition)

gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
pf_data <- dbGetQuery(gameday, pf_query)
dbDisconnect(gameday)

# Basic data.frame for storing park factors
pf_table_skeleton <- as.data.frame(pf_data %>% group_by(stadium, bat_type, bat_hand, game_time) %>% summarise(n()))
colnames(pf_table_skeleton)[colnames(pf_table_skeleton) == 'n()'] <- 'num_pas'

# Function to create data.frame containing park factor and regressed park factor for <event>
regressed_pf <- function(event, logit_model, stabilization_pt) {
  # Predicted league average <event> rate
  event_rate <- sum(predict(logit_model, type='response', re.form=NA)) / nrow(pf_data)
  new_table <- pf_table_skeleton
  new_table['event'] <- event
  new_table['pf'] <- predict(logit_model, newdata=pf_table_skeleton, type='response', re.form=NA) / event_rate
  # If num_pas exceeds the stabilization point then we don't regress data.
  # If num_pas exceeds data then we regress data towards 1 by taking a weighted average
  # NOTE: this regression is not used in the empirical Bayes model
  new_table['regressed_pf'] <- ifelse(new_table$num_pas >= stabilization_pt,
                                      new_table$pf,
                                      new_table$pf*new_table$num_pas/stabilization_pt + 1-new_table$num_pas/stabilization_pt)
  return(new_table)
}


#Singles Contextual Park Factor
pf.single <- glmer(single ~ bat_type + stadium*bat_hand*game_time + (1|batter) + (1|pitcher), data=pf_data, family=binomial, nAGQ=0, verbose=TRUE)
pf_table_single <- regressed_pf(event="single", logit_model=pf.single, stabilization_pt=1000)

#Doubles Contextual Park Factor
pf.double <- glmer(double ~ bat_type + stadium*bat_hand*game_time + (1|batter) + (1|pitcher), data=pf_data, family=binomial, nAGQ=0, verbose=TRUE)
pf_table_double <- regressed_pf(event="double", logit_model=pf.double, stabilization_pt=2000)

#Triples Contextual Park Factor
pf.triple <- glmer(triple ~ bat_type + stadium*bat_hand*game_time + (1|batter) + (1|pitcher), data=pf_data, family=binomial, nAGQ=0, verbose=TRUE)
pf_table_triple <- regressed_pf(event="triple", logit_model=pf.triple, stabilization_pt=2000)

# Homeruns Contextual Park Factor
pf.homerun <- glmer(homerun ~ bat_type + stadium*bat_hand*game_time + (1|batter) + (1|pitcher), data=pf_data, family=binomial, nAGQ=0, verbose=TRUE)
pf_table_homerun <- regressed_pf(event="homerun", logit_model=pf.homerun, stabilization_pt=2000)

# Walks Contextual Park Factor
pf.walk <- glmer(walk ~ bat_type + stadium*bat_hand*game_time + (1|batter) + (1|pitcher), data=pf_data, family=binomial, nAGQ=0, verbose=TRUE)
pf_table_walk <- regressed_pf(event="walk", logit_model=pf.walk, stabilization_pt=500)

# Strikeouts Contextual Park Factor
pf.strikeout <- glmer(strikeout ~ bat_type + stadium*bat_hand*game_time + (1|batter) + (1|pitcher), data=pf_data, family=binomial, nAGQ=0, verbose=TRUE)
pf_table_strikeout <- regressed_pf(event="strikeout", logit_model=pf.strikeout, stabilization_pt=500)

# Combine park factors into one data frame
pf_table <- rbind(pf_table_single, pf_table_double, pf_table_triple, pf_table_homerun, pf_table_walk, pf_table_strikeout)
# Drop unneccessary tables
remove(pf_table_single, pf_table_double, pf_table_triple, pf_table_homerun, pf_table_walk, pf_table_strikeout)

get_posterior <- function() {
  pf_bayes <- pf_table
  pf_bayes['regressed_pf'] <- NULL
  # mle is the estimated success rate in a neutral context
  prior_mle <- prior['alpha', pf_bayes$event] / (prior['alpha', pf_bayes$event] + prior['beta', pf_bayes$event])
  # park adjusted success rate is mle * park factor
  success_rate <- pf_bayes$pf * prior_mle
  num_success <- success_rate * pf_bayes$num_pas
  # Beta-binomial model to get posterior
  posterior_rate <- (prior['alpha', pf_bayes$event] + num_success) / (pf_bayes$num_pas + prior['alpha', pf_bayes$event] + prior['beta', pf_bayes$event])
  # Need to transpose park factors so that it is 1440x1 and not 1x1440
  pf_bayes['pf'] <- t(posterior_rate / prior_mle)[, 'alpha']
  return(pf_bayes)
}

pf_bayes <- get_posterior()
# Constrain pf_bayes to [0.5, 2.0]
pf_bayes['pf'][pf_bayes['pf'] < 0.5] <- 0.5
pf_bayes['pf'][pf_bayes['pf'] > 2.0] <- 2.0
pf_bayes['year_id'] <- year_condition
colnames(pf_bayes)[colnames(pf_bayes)=='event'] <- 'outcome'
 
# Change event names to match gameday database
pf_bayes['outcome'][pf_bayes['outcome'] == 'single'] <- "Single"
pf_bayes['outcome'][pf_bayes['outcome'] == 'double'] <- "Double"
pf_bayes['outcome'][pf_bayes['outcome'] == 'triple'] <- "Triple"
pf_bayes['outcome'][pf_bayes['outcome'] == 'homerun'] <- "Home Run"
pf_bayes['outcome'][pf_bayes['outcome'] == 'walk'] <- "Walk"
pf_bayes['outcome'][pf_bayes['outcome'] == 'strikeout'] <- "Strikeout"

# Overwrite/Append year to gameday.park_factors table
# gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
# pf_year <- year_condition
# deletion_query <- sprintf("DELETE FROM park_factors WHERE year_id=%s;", pf_year)
# dbSendQuery(gameday, deletion_query)
# dbWriteTable(gameday, "park_factors", pf_bayes, append=TRUE, row.names=FALSE, field.type=list(stadium="CHAR(3)", bat_type="CHAR(1)", bat_hand="CHAR(1)", game_time="CHAR(1)", num_pas="MEDIUMINT(4)", outcome="VARCHAR(9)", pf="DOUBLE", year_id="YEAR(4)"))
# dbDisconnect(gameday)

# Create new gameday.park_factors table
# gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
# dbSendQuery(gameday, "DROP TABLE IF EXISTS park_factors;")
# dbWriteTable(gameday, "park_factors", pf_bayes, row.names=FALSE, field.type=list(stadium="CHAR(3)", bat_type="CHAR(1)", bat_hand="CHAR(1)", game_time="CHAR(1)", num_pas="MEDIUMINT(4)", outcome="VARCHAR(9)", pf="DOUBLE", year_id="YEAR(4)"))
# dbSendQuery(gameday, "alter table park_factors add primary key (stadium,bat_type,bat_hand, game_time, outcome, year_id)")
# dbDisconnect(gameday)
