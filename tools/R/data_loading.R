#####Reading Data#####
get_team_id <- function(team){
	query<-paste("select year_id, team_id, name_team_tx from teams WHERE name_team_tx = '",team,"' group by team_id;", sep="")
	rs<-dbSendQuery(mydb, query)
	id<-fetch(rs, n=-1)
	dbClearResult(rs)
	id$team_id
}

#Marlins changed team name in 2010 so can't go back before that
team_id_dict <- function(team_list){
	dict <- list()
	for( team in team_list$Var1 ){
		dict[[team]] = get_team_id(team)
	}
	dict$Marlins<-"MIA"
	dict
}

#team id is hometeam
get_game_pa <- function(date, double_header, team_id){
  game_id<-paste(team_id,date,double_header, sep="")
	query<-paste("select Count(*) AS PA, BAT_TEAM_ID from events WHERE game_id LIKE '",
               game_id,"' GROUP BY BAT_TEAM_ID;", sep="")
	rs<-dbSendQuery(mydb, query)
	id<-fetch(rs, n=-1)
	id_dict<-list()
  #HACK!!! to deal with Marlins changing their name
  if( id$BAT_TEAM_ID[1]=="FLO" ){
    id_dict["MIA"] = id$PA[1]
    id_dict[id$BAT_TEAM_ID[2]] = id$PA[2]
  }else if( id$BAT_TEAM_ID[2]=="FLO" ){
    id_dict[id$BAT_TEAM_ID[1]] = id$PA[1]
    id_dict["MIA"] = id$PA[2]
  }else{
    id_dict[id$BAT_TEAM_ID[1]] = id$PA[1]
    id_dict[id$BAT_TEAM_ID[2]] = id$PA[2]
  }
  dbClearResult(rs)
  
	query<-paste("select INN_CT from games WHERE game_id LIKE '", 
               game_id, "'", sep="")
  rs<-dbSendQuery(mydb, query)
  id<-fetch(rs, n=-1)
  id_dict["INNS"] = id$INN_CT[1]
	dbClearResult(rs)
  
	id_dict
}

add_pa_data <- function(data2, team_dict){
	pa_dict <- as.data.frame(data2$rbi)
	pa_list <- c()
	o.pa_list <- c()
  inns <- c()
	for( i in 1:length(data2[,1]) ){
		row<-data2[i,]
		team_id<-team_dict[[row$team]]
		o.team_id<-team_dict[[row$o.team]]
		pas<-get_game_pa(row$date, row$double.header, team_id)
		pa_list <- c(pa_list, pas[[team_id]])
		o.pa_list <- c(o.pa_list, pas[[o.team_id]])
    inns <- c(inns, pas$INNS)
	}
	pa_dict$home = pa_list
	pa_dict$away = o.pa_list
  pa_dict$inns = inns
	pa_dict
}

team_pa_dict <- function(team_list, data2){
	dict <- list()
	for( team_name in team_list$Var1 ){
		dict[[team_name]] = round(mean(subset(data2, data2$team==team_name)$pa), digits=5)
	}
	dict
}

avg_pa_data <- function(teams, team_dict_pa){
	avg_data <- c()
	for( team in teams ){
		avg_data <- c(avg_data, team_dict_pa[[team]])
	}
	avg_data
}

#doesn't take the vig out
norm<-function(odds){
	new_odds<-c()
	for( odd in odds ){
		new_odds<-c(new_odds, round(odds_to_prob(odd), digits=5))
	}
	new_odds
}

devig<-function(over, under){
	new_over<-norm(over)
	new_under<-norm(under)
	round(subtract_vig(new_over, new_under), digits=5)
}
subtract_vig<-function(over, under){
	over/(over+under)
}

#converts American odds to implied probabilities
#this doesn't take out the vig
#can assume the vig is around 2%?
odds_to_prob<-function(odds){
	if( odds > 0 ){
		(100)/(odds+100)
	}else{
		(-odds)/(-odds+100)
	}
}

is_home_team <- function(row, team_dict){
	team_id<-team_dict[[row$team]]
	query<-paste("select game_id from games WHERE game_id LIKE '",team_id,row$date,row$double.header,"';", sep="")
	rs<-dbSendQuery(mydb, query)
	id<-fetch(rs, n=-1)
	dbClearResult(rs)
	if(length(id$game_id) == 0){
		F
	}else{
		T
	}
}

get_home_teams <- function(data, team_dict){
	indices<-c()
	for( i in 1:length(data[,1]) ){
		if( is_home_team(data[i,], team_dict) ){
			indices<-c(indices, i)
		}
	}
	indices
}

load_function <- function(file="blines.csv"){
	data<-read.csv(file,header=T)
  
	#all the teams that appear
	team_list<-as.data.frame(table(data$team))
	team_dict<-team_id_dict(team_list)
  
	#add a column for if data$team won
	data$win<-data$runs>data$o.runs
	#transform odds into implied win probability for data$team
	data$odds<-devig(data$line, data$o.line)
	data$total.odds<-devig(data$over, data$under)
  data$run.line.odds<-devig(data$run.line, data$o.run.line)
	#data2<-data[seq(2,length(data[,1])-1,2),]
	data2<-data[get_home_teams(data, team_dict),]
	pa_dict<-add_pa_data(data2, team_dict)
	data2$pa<-pa_dict$home
	data2$o.pa<-pa_dict$away
  data2$inns<-pa_dict$inns
	team_dict_pa<-team_pa_dict(team_list, data2)
	data2$pa.mean<-avg_pa_data(data2$team, team_dict_pa)
	write.csv(data2, file=paste("processed-",file, sep=""), row.names=FALSE)
	data2
}

#load database
library(RMySQL)

mydb <- dbConnect(MySQL(), user='root', password='', dbname='retrosheet', host='localhost')
on.exit(dbDisconnect(mydb))
#dbListFields(mydb, 'games')
data2<-load_function("blines.csv")

