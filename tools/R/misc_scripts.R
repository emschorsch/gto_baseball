#http://stackoverflow.com/questions/21380236/cross-validation-for-glm-models-in-r
#Randomly shuffle the data
yourData<-yourData[sample(nrow(yourData)),]

#Create 10 equally size folds
folds <- cut(seq(1,nrow(yourData)),breaks=10,labels=FALSE)

#Perform 10 fold cross validation
for(i in 1:10){
  #Segement your data by fold using the which() function 
  testIndexes <- which(folds==i,arr.ind=TRUE)
  testData <- yourData[testIndexes, ]
  trainData <- yourData[-testIndexes, ]
  #Use test and train data partitions however you desire...
}

#for partial residuals plot
library(car)  
lm_fit<-lm(y~x1+x2+x3)  
crPlots(lm_fit)  

library(dplyr)
attach(data3)
plot(cut(odds, breaks = c(-.02, seq(.3,.7, .05), 1)))

prob_levels <- cut(odds, breaks = c(-.02, seq(.3,.7, .05), 1))
data3$prob_level <- prob_levels
group_by(data3, prob_level) %>% summarise(mean(win))
group_by(data3, prob_level) %>% summarise(n())
group_by(data3, prob_level) %>% summarise(mean(odds))
