library(DBI)
library(RMySQL)

pss <- read.csv("~/baseball/baseball/PSS/sim_scores.csv")
pss['X'] <- NULL

gameday <- dbConnect(RMySQL::MySQL(), dbname='gameday', user='bbos', password='bbos')
dbSendQuery(gameday, "DROP TABLE IF EXISTS pitcher_similarity;")
dbWriteTable(gameday, "pitcher_similarity", pss, row.names=FALSE, field.type=list(pit1="MEDIUMINT(6)", pit2="MEDIUMINT(6)", similarity="DECIMAL(6, 5)", sim_light="DECIMAL(6, 5)", sim_med="DECIMAL(6, 5)", sim_heavy="DECIMAL(6, 5)", cfip="DECIMAL(6, 5)"))
dbSendQuery(gameday, "ALTER TABLE pitcher_similarity ADD PRIMARY KEY (pit1, pit2);")
dbDisconnect(gameday)
