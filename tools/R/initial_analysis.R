#Set working Directory
setwd("/Users/emanuelschorsch/Documents/Baseball")

#####Reading Data#####
data2<-read.csv("processed-blines.csv", header=T)

#I believe this shows a somewhat linear relationship between the odds and who wins the game
mean_plot(data2$odds, data2$win)

#returns the accuracy rate. Doesn't tell you how many qualifying events there were
vegas_cutoff <- function(margin){
  vegas.error <- (data2$odds>(.5+margin) & data2$win == F) | (data2$odds<(.5-margin) & data2$win == T)
  qualified <- data2$odds>(.5+margin) | data2$odds<(.5-margin)
  #error rate:
  1-sum(vegas.error)/sum(qualified)
}

#can see vegas accuracy improves as restrict to more extreme odds
vegas_cutoff(0.05)
vegas_cutoff(0.1)
vegas_cutoff(0.15)


#predicting fraction of home team runs out of total
true_y<-data2$runs/(data2$runs+data2$o.runs)
model<-lm(true_y~odds+total, data=data2)
summary(model)

#Can see a somewhat linear relationship, but it's not particularly strong
hex_plot(data2$odds, true_y)

############
#REGRESSION analysis
############
#predicts rbi decently, with an adj R^2 of approx .05717
model<-lm(rbi~odds+total+total.odds+run.line.runs+run.line.odds, data=data2)
summary(model)

#This basic model has adj R^2 of .0551
model<-lm(data2$rbi~data2$odds+data2$total)
summary(model)

#!!!! RBI and PA have same problem of extreme non-normality
qqnorm(model$residuals)
qqline(model$residuals)

#predicts pa poorly, with an R^2 of approx .0176
model<-lm(pa~odds+total+total.odds+pa.mean, data=data2)
summary(model)

#Try out the LOESS not sure if this is statistically sound, might be overfitting
model<-loess(pa~odds+total+total.odds+pa.mean, data=data2)
summary(model)
#R^2 is up to .0195 with LOESS
##### Not sure if this is valid way to measure a pseudo R^2
cor(data2$pa, fitted(model))^2


#############
###Checking Assumptions
##############

#the mean run levels seem to have a linear relationship with predicted total
mean_plot(data2$total, data2$run_total)
#Weak relationship with PA for data2, cor of .52
mean_plot(data2$total, data2$pa, yrange=c(35,50))
#Realized its because of extra innings
#data 3 removes games != 9 innings. Relationship is a little stronger, cor of .63
#The plots are misleading if you don't make sure the ranges are the same
mean_plot(data3$total, data3$pa, yrange=c(35,50))
#For some reason o.pa has cor of .711
mean_plot(data3$total, data3$o.pa, yrange=c(35,50))


#boxplot representation to see relationship between run_total and over under line
par(bg="cornsilk")
boxplot(split(data2$run_total,data2$total), col="lavender", notch=TRUE)

## Conditioning plots. Don't seem particularly useful
coplot(run_total ~ total | odds, data = data2, pch = 21, bg = "green3")



#################
###Check distribution assumptions. We look at the distribution of y.
## really only care about distribution of residuals but they seem to have a basically
# 1-1 correspondence. Is it cause I'm not doing any transformations?
#################
#######
#Fitting the right distribution
#link1 (super useful!!): http://www.r-project.org/conferences/useR-2009/slides/Delignette-Muller+Pouillot+Denis.pdf
#
#######
library(fitdistrplus)
#seems like rbi is close to a gamma distribution
descdist(data2$rbi,boot=1001)
#Try to fit a gamma
fg.mle<-fitdist(data2$rbi,"gamma",method="mme")
summary(fg.mle)
plot(fg.mle)

#seems like rbi is somewhere between negative binomial and poisson
descdist(data2$rbi, discrete=TRUE)

#fit it
fnbinom<-fitdist(data2$rbi,"nbinom")
plot(fnbinom)

#much worse
fnbinom2<-fitdist(data2$rbi,"pois")
plot(fnbinom2)

x.teo2<-rnbinom(n=9625,size=4, prob=1/(2.03))
x.teo<-rnbinom(n=9625,size=4, mu=4.13) ## theorical quantiles from a
#negative binomial with mu=4.13
qqplot(x.teo2, data2$rbi,main="QQ-plot distr. NBinom") ## QQ-plot
abline(0,1) ## a 45-degree reference line is plotted

#########
#Now for PA
#R^2 of .017
model<-lm(pa~odds+total+total.odds+pa.mean, data=data2)
summary(model)

#R^2 of .035
model2<-lm(pa~odds+total+total.odds+pa.mean, data=data3)
summary(model2)

#See residuals are not any known distribuotion for data2
descdist(model$residuals,boot=1001)
#When we restrict to 9 innings in data 3, we get close to normal, maybe lognormal
descdist(model2$residuals, boot=1001)


#Looks like total is kinda normal
descdist(data2$total, boot=1001, discrete=T)

#run_total isn't though
descdist(data2$run_total, discrete=T)



##########
#try out the Poisson Regression
#########
model1<-glm(pa~odds+total, family=poisson, data=data2)
model<-glm(pa~odds+total+total.odds+pa.mean, family=poisson, data=data2)
summary(model)
1-(model$deviance/model$null.deviance)
### var(model$residuals) == .02 

press(model)


#The cv package
model1a<-glm(pa~odds+total, data=data2, family=poisson())
model2a<-glm(pa~odds+total+total.odds+pa.mean, data=data2, family=poisson())

library(MASS)
modelRBI<-glm.nb(rbi~odds+total+total.odds, data=data2)
summary(modelRBI)
#.0565
cor(data2$rbi, fitted(modelRBI))^2
#Is this a good metric for good fit?
#Is this RMSE? 2.797
#problem is residuals are in terms of the linear model and not the exponentiated model
sqrt(mean((data2$rbi - fitted(modelRBI2))^2))
# MAE is 1.477
sqrt(mean(abs(data2$rbi - fitted(modelRBI2))))
#baseline RMSE 2.882
sqrt(mean((data2$rbi - data2$temp)^2))
#baseline MAE is 1.501
sqrt(mean(abs(data2$rbi - data2$temp)))
sd(data2$rbi - fitted(modelRBI2))

modelRBI2<-glm.nb(rbi~odds+total+total.odds+run.line.runs+run.line.odds, data=data2)
summary(modelRBI2)
#.0578 prediction all significant though
cor(data2$rbi, fitted(modelRBI2))^2

m3 <- update(modelRBI2, . ~ . - run.line.runs)
#anova shows that run.line.runs is a significant predictor
anova(modelRBI2, m3)

m4 <- glm(rbi~odds+total+total.odds+run.line.runs+run.line.odds, data=data2)
# chissq strongly suggests that negative binomial is better
pchisq(2 * (logLik(modelRBI2) - logLik(m4)), df = 1, lower.tail = FALSE)

(est <- cbind(Estimate = coef(modelRBI2), confint(modelRBI2)))
#shows us our confidence intervals in an interpretable manner
exp(est)


cv.err <- cv.glm(data2, model2, K=10)

