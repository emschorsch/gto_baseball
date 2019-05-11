#Set working Directory
setwd("/Users/emanuelschorsch/baseball")

library(dplyr)

analyze_by_decile <- function(pred_data){
  prob_levels <- cut(pred_data$prob_home_win, breaks = c(-.02, seq(.3,.7, .05), 1))
  pred_data$home_win <- pred_data$home_score > pred_data$away_score
  pred_data$prob_level <- prob_levels
  print(group_by(pred_data, prob_level) %>% summarise(mean(home_win)))
  print(group_by(pred_data, prob_level) %>% summarise(n()))
  print(group_by(pred_data, prob_level) %>% summarise(mean(prob_home_win)))
  return()
}


predictions1 <- read.csv("simulation_error2014_1.csv")
predictions1000 <- read.csv("simulation_error2014_1000.csv")
predictions100 <- read.csv("simulation_error2014_100.csv")
predictions10 <- read.csv("simulation_error2014_10.csv")


attach(predictions100)

home_win <- home_score > away_score
labels <- home_win
predictions <- prob_home_win
# Gives predictions on y-axis. So of (501+627=1128) predicted home_win 627 actually are.
# Of (640+658=1298) predicted home_loss 640 actually were true.
# Overall a 52.22% accuracy compared to 58.3% for implied odds from vegas lines
# 52.9% if the simulator doesn't include steals
(conf_matrix <- as.matrix(table(factor(predictions>0.5, levels=c(F, T)), labels)))
(accu <- (conf_matrix[1,1]+conf_matrix[2,2])/sum(conf_matrix))

sim_away <- pred_away_score
plot(table(sim_away), ylim=c(0,370), xlim=c(0,16), ylab="count")
plot(table(away_score), ylim=c(0,370), xlim=c(0,16), ylab="count")
#Seems to overstimate the extremes
# 0 runs and 7+ are significantly overestimated
# 1-5 are all underestimated

sim_home <- pred_home_score
plot(table(sim_home), ylim=c(0,370), xlim=c(0,16), ylab="count")
plot(table(home_score), ylim=c(0,370), xlim=c(0,16), ylab="count")
#This sim overestimates 1 alot and 2-4 a little
# underestimates 5-6 alot seems to understimate 9+ a little also

#Histogram of levels with the right breaks
plot(cut(home_score, breaks = c(-.02, 0:10, 100)))
plot(cut(prob_home_win, breaks = c(-.02, seq(.3,.7, .05), 1)))

data3 <- read.csv("vegas_lines.csv")
group_by(data3, prob_level) %>% summarise(mean(win))
group_by(data3, prob_level) %>% summarise(mean(odds))
group_by(data3, prob_level) %>% summarise(n())

(conf_matrix <- as.matrix(table(factor(data3$odds>0.5, levels=c(F, T)), data3$win)))
(accu <- (conf_matrix[1,1]+conf_matrix[2,2])/sum(conf_matrix))
