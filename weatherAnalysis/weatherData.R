# https://cran.r-project.org/web/packages/weatherData/weatherData.pdf
# install.packages("weatherData")
# install.packages("lubridate")

setwd("/Users/emanuelschorsch/baseball/weatherAnalysis")
options(max.print=500)

library("weatherData")
ls("package:weatherData")
library("lubridate")
library(dplyr)

atlanta braves: Grant Park (KGAATLAN40) closest one is KFTY (10 miles)
arizona diamondbacks: APRSWXNET (ME7902) closest one is KPHX
baltimore MD: Riverside (KMDBALTI81) closest one is KDMH
chicago whitesox: U.S. Cellular Field (KILCHICA30) closest one is KMDW (7 miles)
chicago cubs: Wrigleyville (KILCHICA60) closest one is KORD (14 miles)
cleveland indians: Buckeye Woodhill (KOHCLEVE34) closest one is KCGF (16 miles away)
la dodgers: Downtown Los Angeles (KCALOSAN8) closest one is KCQT (6 miles)
kansas city: AMR Scrap Recycling Yard (KMOKANSA61) closest one is KMKC (10 miles)
milwaukee brewers: Johnson Woods (KWIMILWA51) closest one is KMKE (10 miles) (retractable)
mineappolis twins: North Loop (KMNMINNE88) closest one is KMIC (12 miles) or KMSP (11 miles)
ny mets: Flushing (KNYNEWYO364) closest one is KLGA
philly: Broad and Washington (KPAPHILA21) closest one is KPHL
pittsburg pirates: Brighton Heights (KPAPITTS104) closest one is KAGC (11 miles away)
seattle mariners: Belltown (KWASEATT398) closest one is KBFI (5 miles) (retractable)
st luis cardinals: St Louis, MO (KMOSAINT84) closest one is KCPS (5 miles)
sf giants: SOMA South Park (KCASANFR327) closest one is KOAK (20 miles, also in oakland vs sf!)
texas rangers: North Arlington (KTXARLIN40) closest one is KGPM (6 miles)
yankees: Marcus Garvey Park (KNYNEWYO139) closest one is KNYC (3 miles)

##################
#TODO: should we include Cleveland if its 16 miles away?
#What about Oakland and minneapolis
#Seattle is retractable roof. don't include it?
###################
stadium_dict <- list(NA, "KDMH", NA, "KMDW", NA, NA, "KMSP", NA,
                     NA, "KGPM", NA, "KPHX", "KFTY", NA, NA, NA,
                     "KCQT", "KLGA", "KAGC", NA, NA, NA, NA, NA,
                     NA, NA, "KPHL", NA, NA, "KLGA",
                     NA, NA, "KNYC")

#1-10 anaheim, baltimore, boston, chicago sox, cleveland, kansas city, minneapolis, oakland
#2-20 st persberg FL, Arlington TX, Toronto, Phoenix, Atlanta, wrigley, denver, miami
#22-2395 LA, Flushing, Pittsburgh, Milwaukee, Seattle, Houston, Detroit, SF
#2504-2539 Cincinatti, San Diego, Philly, RFK Memorial Stadium, St Luis, Flushinng, 
# Nationals park, Minneapolis, Bronx, 
names(stadium_dict) <- as.character(c(1, 2, 3, 4, 5, 7, 8, 10, 
                                      12, 13, 14, 15, 16, 17, 19, 20,
                                      22, 25, 31, 32, 680, 2392, 2394, 2395,
                                      2602, 2680, 2681, 2721, 30, 3289, 
                                      3309, 3312, 9))

transformWeather <- function(data){
  data$Date <- as.Date(trunc(data$Time, "days"))
  data$PrecipitationIn <- as.numeric(data$PrecipitationIn)
  data$PrecipitationIn[is.na(data$PrecipitationIn)] <- 0
  data$Time <- hour(data$Time) + minute(data$Time)/60
  data
}

# baltimore
# 10 days are missing from the Wunderground website
d4 <- getWeatherForDate("KDMH", start_date="2005-02-01", end_date="2015-10-05",
                        opt_detailed = TRUE,
                        opt_all_columns = TRUE)
d4a <- transformWeather(d4)

# mets
d3 <- getWeatherForDate("KLGA", start_date="2005-02-01", end_date="2015-10-05",
                        opt_detailed = TRUE,
                        opt_all_columns = TRUE)
d3a <- transformWeather(d3)

# chicago sox
d5 <- getWeatherForDate("KMDW", start_date="2005-02-01", end_date="2015-10-05",
                        opt_detailed = TRUE,
                        opt_all_columns = TRUE)
d5a <- transformWeather(d5)

# minneapolis
d6 <- getWeatherForDate("KMSP", start_date="2005-02-01", end_date="2015-10-05",
                        opt_detailed = TRUE,
                        opt_all_columns = TRUE)
d6a <- transformWeather(d6)

# pittsburg
d7 <- getWeatherForDate("KAGC", start_date="2005-02-01", end_date="2015-10-05",
                        opt_detailed = TRUE,
                        opt_all_columns = TRUE)
d7a <- transformWeather(d7)

# philly
d8 <- getWeatherForDate("KPHL", start_date="2007-02-01", end_date="2015-10-05",
                        opt_detailed = TRUE,
                        opt_all_columns = TRUE)
d8a <- transformWeather(d8)

# yankees
d9 <- getWeatherForDate("KNYC", start_date="2007-02-01", end_date="2015-10-05",
                        opt_detailed = TRUE,
                        opt_all_columns = TRUE)
d9a <- transformWeather(d9)

#All the weather data
weatherData <- list(KLGA=d3a, KDMH=d4a, KMDW=d5a, KMSP=d6a, KAGC=d7a, 
                    KPHL=d8a, KNYC=d9a)


#home_time is also local time. time is always EST
# Weather is local time
select gameName, venue, venue_id, IF(reason='Rain', 1, 0) AS rain, time, home_time, home_ampm, forecast, temperature, windDirection, windMPH, gameLength, status 
FROM gameDetail JOIN gameConditions Using(gameName) 
WHERE year > 2006 AND game_type = 'R' ORDER BY gameName DESC
INTO OUTFILE 'games.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n';
#/var/lib/mysql/gameday/games.csv


ignore_na_sum <- function(col){
  sum(col, na.rm = TRUE)
}

counts <- function(col, col2){
  sum(col > 0.0, na.rm = TRUE)/6.0
}

# Sets precip to 0 if its more than 2 hours before the game or 4 hours after
adjustPrecip <- function(info){
  game_start <- as.numeric(info[["Game_Start_Time"]])
  precip <- info[["PrecipitationIn"]]
  time <- as.numeric(info[["Time"]])
  if( is.na(game_start) || is.na(time) ){
    return(NA)
  }
  
  if( (time - game_start) > 4 ){ #more than 4 hours after
    return(NA)
  }else if ( (game_start - time) > 2){ #more than 2 hours before
    return(NA)
  }else{
    return(precip)
  }
}

feature_extraction <- function(info){
  adj_rain <- as.numeric(apply(info[,c("Game_Start_Time", "Time", "PrecipitationIn")], 
                               1, adjustPrecip))
  t2 <- mutate(info, rain2 = adj_rain) %>% 
    group_by(Date, Game_Start_Time, trunc(Time)) %>% 
    filter(!is.na(Game_Start_Time)) %>%
    summarise(hourly_rain=ignore_na_sum(rain2)) %>%
    summarise(total=ignore_na_sum(hourly_rain), fraction_raining = counts(hourly_rain))
  results2 <- select(t2, Game_Start_Time, total, fraction_raining)
  #   get average Visibility
  '
  adj_rain_totals <- aggregate(adj_rain, by=list(info$Date, info$Game_Start_Time), 
  FUN=ignore_na_sum)
  adj_rain_counts <- aggregate(data.frame(adj_rain, info$Time), 
  by=list(info$Date, info$Game_Start_Time), FUN=counts)
  #info[which(info$Date == "2012-04-22"), c("Date", "Game_Start_Time", "Time", "PrecipitationIn")]
  results <- cbind(adj_rain_totals, adj_rain_counts$adj_rain)
  #2008-09-12 there were 6 rained out games!!
  '
  names(results2) <- c("Date", "Start_Hour", "total", "fraction_raining")
  return(results2)
}


#Regular season games
game_data <- read.csv("games.csv", header=T, stringsAsFactors=F)
game_data$Date <- as.Date(substr(game_data$gameName, 5, 14), "%Y_%m_%d")
# Hack to deal with misrecorded double headers
game_data$home_time[game_data$time == "Gm 2:00"] <- "Gm 2:00"
game_data$Date_Time <- ymd_hms(paste(game_data$Date, game_data$home_time, game_data$home_ampm))
game_data$Start_Hour <- hour(game_data$Date_Time)
game_data$total <- NA
game_data$fraction_raining <- NA


#TODO: Create fake copies of the games that are rained out

# Initialize empty dataframe
rainout_data <- game_data[0,]

for(venue_id in as.character(unique(game_data$venue_id))){
  # for each venue extract the features and then merge it back into game_data
  weatherStation <- stadium_dict[[venue_id]]
  if(!is.null(weatherStation) && !is.na(weatherStation) && 
       weatherStation %in% names(weatherData)){
    weather <- weatherData[[weatherStation]]
    relevantGames <- game_data[game_data$venue_id == venue_id, ]
    featureNames <- c("total","fraction_raining")
    relevantGames <- relevantGames[,!(names(relevantGames) %in% featureNames)]
    #merge station
    gameTimes <- data.frame(relevantGames$Start_Hour, relevantGames$Date)
    names(gameTimes) <- c("Game_Start_Time", "Date")
    # There could be a doubleheader. WATCH OUT!!
    temp <- merge(gameTimes, weather, by=c("Date"))
    features <- feature_extraction(temp)
    # Does merge preserve the order of relevantGames, cause otherwise this is incorrect
    rainout_data <- rbind(rainout_data, 
                          merge(relevantGames, features, by=c("Date", "Start_Hour"), all.x=T))
  }
}

table(filter(rainout_data, fraction_raining <= 0.25)$rain) #12/65
table(filter(rainout_data, fraction_raining >= .5)$rain) #38/65


#The better performing model is on Azure ML
#TODO: add in lightning data using presence of string thunderstorm as a proxy

# basic model
rainout_data$rain <- factor(rainout_data$rain)
mylogit <- glm(rain ~ fraction_raining + total, data = rainout_data, family = "binomial")

#Old stuff
rain_by_date <- tapply(as.numeric(d3$PrecipitationIn), as.Date(trunc(d3$Time, "days")), FUN=ignore_na_sum)
plot(table(rain_by_date), ylim=c(0,20), xlim=c(0,5))

head(d3,n=1)[,c(1,3,11,12)]
gameTimes <- data.frame(game_data$time, game_data$Date)
names(gameTimes) <- c("Game_Start_Time", "Date")


oct2<- as.numeric(d3$PrecipitationIn)[as.Date(trunc(d3$Time, "days")) == "2015-10-02"]
d3$Time[as.Date(trunc(d3$Time, "days")) == "2015-10-02"]

#getWeatherForDate("KNYNEWYO364", start_date="2014-02-01", station_type="ID")