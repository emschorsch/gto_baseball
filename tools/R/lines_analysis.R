#Introduction to R

#Set working Directory
setwd("/Users/emanuelschorsch/Documents/Baseball")

library(dplyr)

#####Reading Data#####
data2<-read.csv("processed-blines.csv", header=T)
data2$run_total <- data2$runs + data2$o.runs
data3<-filter(data2, inns==9)



###################
###PA analysis
###################
par(mfrow=c(1,1))
#pa has cor of .637
mean_plot(data3$total, data3$pa, yrange=c(35,45))
#For some reason o.pa has cor of .711
mean_plot(data3$total, data3$o.pa, yrange=c(35,45))

library(fitdistrplus)
#looks like pa is NB but close to normal
descdist(data3$pa-24,boot=1001, discrete=T)

#looks like o.pa is poisson. Neeed to predict that since o.pa has two
#Processes in play. There PAs in the first 8 innings and then the last inning.
#Should maybe get data for PA/RBIs per inning
descdist(data3$o.pa,boot=1001, discrete=T)

#bad fit
fnbinom<-fitdist(data3$pa-24,"nbinom")
plot(fnbinom)

#also bad fit
fnbinom2<-fitdist(data3$pa-24,"pois")
plot(fnbinom2)

#Linear model first, looks like run.line stuff is insignificant
#R^2 of .0357, AIC of 49594
model<-glm(pa~odds+total+total.odds+run.line+run.line.odds+pa.mean, data=data3)
summary(model)
plot(model)

#Poisson model, AIC of 49516
model2<-glm((pa)~odds+total+total.odds+run.line+run.line.odds+pa.mean, 
            data=data3, family=poisson)
summary(model2)
#plot(model2)
##### Not sure if this is valid way to measure a pseudo R^2
##R^2 of .0357
cor(data3$pa, fitted(model2))^2

#This is 1 if we model pa, and 0 if we model pa-24
1-pchisq(model2$deviance, model2$df.residual)

#Poisson model
model2a<-glm(pa~odds+total+total.odds+run.line+run.line.odds+pa.mean, 
            data=data3, family=quasipoisson())
summary(model2a)

#now NB model
library(MASS)
model3<-glm.nb(pa-24~odds+total+total.odds+run.line+run.line.odds+pa.mean, 
               data=data3, init.theta=1, start=model2a$coef)
summary.glm(model3)
##R^2 of .0357, 49309
cor(data3$pa, fitted(model3))^2

library(qpcR)
#Takes 10+ mins to run, essentially leave one out cross validation
#http://www.inside-r.org/packages/cran/qpcR/docs/PRESS
evals<-PRESS(model3, verbose = FALSE)


library(gamlss)
library(gamlss.tr)
gen.trun(par=24, family="PO", name="PA", type="left")
gen.trun(par=24, family="NBI", name="NB", type="left")
model4<-gamlss(pa~odds+total+total.odds+run.line+run.line.odds+pa.mean, 
               data=data3, family=NBINB)
summary(model4)

descdist(residuals(model3,"deviance"), boot=1001, discrete=T)

#bad fit
fnbinom<-fitdist(model3$residuals,"nbinom")
plot(fnbinom)

#also bad fit
fnbinom2<-fitdist(model3$residuals,"pois")
plot(fnbinom2)

#############
###trying out sandwich
########
cov.m1 <- vcovHC(model3, type="HC0")
std.err <- sqrt(diag(cov.m1))
r.est <- cbind(Estimate= coef(model3), "Robust SE" = std.err,
               "Pr(>|z|)" = 2 * pnorm(abs(coef(model3)/std.err), lower.tail=FALSE),
               LL = coef(model3) - 1.96 * std.err,
               UL = coef(model3) + 1.96 * std.err)
r.est

#check if model is goood
with(model3, cbind(res.deviance = deviance, df = df.residual,
               p = pchisq(deviance, df.residual, lower.tail=FALSE)))

