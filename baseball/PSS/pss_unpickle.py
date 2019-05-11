import pickle
import pandas as pd


pss_dict = pickle.load(open("pss_dict.pickle", "rb"))
pss = []
for pit1 in pss_dict.keys():
    for pit2 in pss_dict[pit1].keys():
        pss.append([pit1, pit2, pss_dict[pit1][pit2]])

pss_frame = pd.DataFrame(pss, columns=["pit1", "pit2", "similarity"])
pss_heavy = pss_frame[pss_frame["similarity"] >= .5]

pss_frame.to_csv("pss_scores.csv", header=True, index=False)
pss_heavy.to_csv("pss_heavy.csv", header=True, index=False)



from MySQLdb import connect
db = connect(host="localhost",  # your host, usually localhost
            user="bbos",       # your username
            passwd="bbos",     # your password
             db="retrosheet")   # name of the data base
# Cursor objects let you execute all the queries you need
cur = db.cursor()
#sql_query = pss_frame.to_sql("pitcher_similarity2", db, flavor="mysql")

#part 1
CREATE TABLE pitcher_similarity3 (PRIMARY KEY (pit1, pit2)) select pit1, pit2, 1.00000 AS similarity FROM pitcher_similarity limit 0;

#sql query
LOAD DATA LOCAL INFILE 'pss_heavy.csv'
INTO TABLE pitcher_similarity3
FIELDS TERMINATED BY ','
    ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(pit1, pit2, similarity)

CREATE TABLE pitcher_similarity2a (PRIMARY KEY (pit1, pit2))
select * from pitcher_similarity2;

DROP TABLE pitcher_similarity2;

CREATE TABLE pitcher_similarity2 (PRIMARY KEY (pit1, pit2))
select p1.retrosheet_id AS pit1, p2.retrosheet_id AS pit2, similarity
FROM id_map p1
INNER JOIN pitcher_similarity2a ON p1.mlb_id=pit1
INNER JOIN id_map p2 ON p2.mlb_id=pit2
ORDER BY pit1, pit2;

CREATE TABLE pitcher_similarity3 (PRIMARY KEY (pit1, pit2))
select * from pitcher_similarity2 where similarity >= .5;

