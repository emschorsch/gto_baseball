# High Density Scatterplot with Binning
library(hexbin)
hex_plot <- function(x1, y1=NULL){
  bin<-hexbin(x1, y1, xbins=30) 
  plot(bin, main="Hexagonal Binning")
}


#assume x and y are indexed the same
mean_plot <- function (x, y, yrange=c(0,0)){
  x_level <- c()
  mean_y <- c()
  freq <- as.data.frame(table(x))$Freq
  for( x_val in as.data.frame(table(x))$x ){
    x_level <- c(x_level, as.numeric(x_val))
    mean_y <- c(mean_y, mean( y[which(x==x_val)] ))
  }
  
  #hack to check if yrange has been passed in
  if(yrange[1] == yrange[2]){
    symbols(x=x_level, y=mean_y, circles=sqrt(freq/pi), 
            inches=1/3, ann=F, bg="steelblue2", fg=NULL)
  }else{
    symbols(x=x_level, y=mean_y, circles=sqrt(freq/pi), 
            inches=1/3, ann=F, bg="steelblue2", fg=NULL, ylim=yrange)
  }
  
  cor(mean_y, x_level)
}

mean_plot(data2$total, data2$run_total)

mean_density_plot <- function(x, y){
  #Plot the density functions of y against different x levels
  par(mfrow=c(2,2))
  
  x_levels <- as.data.frame(table(x))$x
  if( length(x_levels) > 30 ){
    stop("Too many x_levels to plot")
  }
  for( x_val in x_levels ){
    qualified <- y[which(x==x_val)]
    if( length(qualified) > 15){
      plot(density(qualified), sub=x_val)
    }
  }
  par(mfrow=c(1,1))
}

##################
#Get PRESS, predictive R^2
# Seems to not work with glm, figure out why
press <- function(model){
  #predictive R^2
  pr <- residuals(model)/(1 - lm.influence(model)$hat)
  PRESS <- sum(pr^2)
  PRESS

  # anova to calculate residual sum of squares
  my.anova <- anova(model)
  tss <- sum(my.anova$"Sum Sq")
  # predictive R^2
  pred.r.squared <- 1 - PRESS/(tss)
  pred.r.squared
}


temp = read.table("../../../baseball/zips_ros_batters05.06.2015", sep=",", header=T)
