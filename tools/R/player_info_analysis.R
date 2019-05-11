#Set working Directory
setwd("/Users/emanuelschorsch/baseball/optimizer")

library(dplyr)

lineups <- read.csv("predicted_lineups.csv")
temp <- group_by(lineups, Lineup) %>% filter(row_number() <= 1)
summary(temp$actual.total)
as.data.frame(temp)
sum(temp$actual.total > temp$Lineup.total)
temp[head(select(as.data.frame(temp), actual.total, Lineup) %>% arrange(desc(actual.total)))$Lineup,]

#####Reading Data#####
player_data<-group_by(read.delim("playerinfo.csv", header=T, sep=";"))

player_data<-group_by(read.delim("playerinfo_9_28_14.csv", header=T, sep=";"))
player_data<-group_by(read.delim("playerinfo_9_27_14.csv", header=T, sep=";"))
player_data<-group_by(read.delim("playerinfo_10_01_15.csv", header=T, sep=";"))

table(player_data$DK.sal)
plot(player_data$DK.sal, player_data$DK.pts)
cor(player_data$DK.sal, player_data$DK.pts, use="complete.obs")
plot(table(player_data$DK.sal), ylim=c(0,62))


#Linear programming
lineuplab uses a combination of interactive N-2D trees, recursion, linear programming, and other custom mathematics designed specifically for DFS”


