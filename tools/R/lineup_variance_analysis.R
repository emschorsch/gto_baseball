#Set working Directory
setwd("~/baseball")

library(dplyr)

home_game_1 <- read.csv("dk_scores_home_1_50000.csv")
away_game_1 <- read.csv("dk_scores_away_1_50000.csv")
home_game_2 <- read.csv("dk_scores_home_2_50000.csv")
away_game_2 <- read.csv("dk_scores_away_2_50000.csv")

summary(home_game_1)
summary(home_game_2)

#no correlation between games
cor(home_game_1$p1, home_game_2$p1)
#correlation goes down as player spot in lineup diverges
cor(home_game_1$p1, home_game_1$p2)
cor(home_game_1$p1, home_game_1$p5)

# Correlation between players and opposing pitchers is < -.3 for all
cor(home_game_1$p1, away_game_1$pitcher)
# pitchers are correlated at -.16 (prob cause of win pts)
cor(home_game_1$pitcher, away_game_1$pitcher)

# Get a summary of the lineup totals
summary(rowSums(home_game_1)) # median is 75.75
#first quartile stays around the same from 5000 to 50,000
# third quartile increases by 3 from 5000 samples to 50,000
summary(rowSums(home_game_1[1:5000,])) # median is 74.75
# We see the sum of the medians is not close to the median of the sums
apply(home_game_1, 2, median)
sum(apply(home_game_1, 2, median)) # sum of medians 62.1

par(mfrow=c(1,2))
plot(table(home_game_1$p1))
plot(table(home_game_2$p1))
par(mfrow=c(1,1))


library(fitdistrplus)
# seems like batters are nbinom and pitchers are basically normal
descdist(home_game_1$p1,boot=1001)
descdist(home_game_1$p1,discrete=TRUE)
# What about the sum of batter performance
descdist(rowSums(home_game_1[,1:2]),discrete=TRUE)

# What if independent?
descdist(home_game_1$p1+home_game_2$p1,discrete=TRUE)

# Seems sufficiently close to normal.
# Skew is < .5 so we can prob use sd approximations to get quantiles
descdist(rowSums(home_game_2), discrete=TRUE)

# nbinom fits much better than pois
fg.mle<-fitdist(home_game_1$p2,"nbinom",method="mme")
summary(fg.mle)
plot(fg.mle)

# normal fits pretty well. mean=13.7 and sd=10.1
fg.mle<-fitdist(home_game_1$pitcher,"norm",method="mme")
summary(fg.mle)
plot(fg.mle)

# What about the sum of batter performance ?
# nbinom fits shockingly well. It's starting to get a little close to normal.
# How come this works even though they're correlated?
fg.mle<-fitdist(rowSums(home_game_1[,1:9]),"nbinom",method="mme")
summary(fg.mle)
plot(fg.mle)

################
#Trying to discover formula for adding NB if independent
# size 1.568 mu 8.179
fg.mle<-fitdist(home_game_1$p1,"nbinom",method="mme")
summary(fg.mle)
plot(fg.mle)

# size 1.493, mu 7.883
fg.mle<-fitdist(home_game_2$p1,"nbinom",method="mme")
summary(fg.mle)
plot(fg.mle)

# size 3.066 mu 16.062.
fg.mle<-fitdist(home_game_1$p1+home_game_2$p1,"nbinom",method="mme")
summary(fg.mle)
plot(fg.mle)
#Very close to just adding the size and mu
# Held for p2s as well. The mu seems to be exactly added.
# the size is off by around .04 in each

################
# Seems like mu is the mean of the dataset being fit
#Trying to discover formula for adding NB if dependent
# size 1.568 mu 8.179
# mle gives significantly different estimates for size. Does that matter?
fg.mle<-fitdist(home_game_1$p3,"nbinom",method="mme")
summary(fg.mle)
plot(fg.mle)

# size 1.545, mu 8.387
fg.mle<-fitdist(home_game_1$p2,"nbinom",method="mme")
summary(fg.mle)
plot(fg.mle)

# size 2.7 mu 16.567.
fg.mle<-fitdist(home_game_1$p1+home_game_1$p2,"nbinom",method="mme")
summary(fg.mle)
plot(fg.mle)
#It seems to be (size1 + size2)*(1-cor(p1, p2))
# For p1, p6 mu was above by .2 and size was above by .02
# For p1, p5 this was above by .06
# for p1, p2 was above by .02
# Held for p2s as well. The mu seems to be exactly added.
# the size is off by around .04 in each
