#!/usr/bin/python


import scrapy
from scrapy.crawler import CrawlerProcess

import pandas as pd

import datetime
import os
now = datetime.datetime.now()
cur_year = str(now.year)
cur_date = "%d%02d" % (now.month, now.day)
directory = os.path.dirname(os.path.abspath(__file__)) + '/../fixtures/'
file_format = directory + "lineups/{}/playerInfo_{}.csv"
filename = file_format.format(cur_year, cur_date.lstrip("0"))


# define a spider
class BaseballPressSpider(scrapy.Spider):
    name = "baseballpress"
    allowed_domains = ["baseballpress.com"]
    start_urls = [
        "http://www.baseballpress.com/lineups",
    ]

    def parse(self, response):
        player_data = [["game_id", "BASEBALLPRESSTEAM", "Name", "MLB_ID", "Position",
                        "bat_hand", "pit_hand", "Bat order", "starter"]]

        all_lineups = response.selector.xpath('//div[@class="main-lineup showall"]')[0]
        games = all_lineups.xpath('.//div[@class="game clearfix"]')
        for i, game in enumerate(games):
            game_id = i
            lineups = game.xpath('.//div/div[@class="players"]')
            teams_data = game.xpath('.//div[@class="team-data"]')
            for j in range(2):
                team = teams_data[j]
                team_info = team.xpath('.//a')[0]
                team_id = team_info.xpath('@href').extract()[0].split('/')[-1]

                # Handle batter info
                lineup_data = lineups[j]
                players_info = lineup_data.xpath('.//div[a/@class="player-link"]')
                for player_info in players_info:
                    name = player_info.xpath('a/text()').extract()[0]
                    mlb_id = player_info.xpath('a/@data-mlb').extract()[0]
                    misc_info = player_info.xpath('text()').extract()
                    # Batting order starts at 0 so subtract one
                    bat_order = int(misc_info[0].strip().rstrip('.')) - 1
                    hand_text, pos = misc_info[-1].split()[:2]
                    bat_hand = hand_text.strip().lstrip('(').rstrip(')')
                    assert(bat_hand in ['L', 'R', 'S'])
                    player_data.append([game_id, team_id, name, mlb_id, pos,
                                        bat_hand, '', bat_order, 1])

                # Handle pitcher info
                pitcher_info = team.xpath('.//div[a/@class="player-link"]')[0]
                pitcher_name = pitcher_info.xpath('a/text()').extract()[0]
                mlb_id = pitcher_info.xpath('a/@data-mlb').extract()[0]
                hand_text = pitcher_info.xpath('text()').extract()[0]
                pit_hand = hand_text.strip().lstrip('(').rstrip(')')
                assert(pit_hand in ['L', 'R', 'S'])

                player_data.append([game_id, team_id, pitcher_name, mlb_id,
                                    'P', '', pit_hand, '', 1])

        players_data = pd.DataFrame(player_data[1:], columns=player_data[0])
        players_data.to_csv(filename, index=False)


def run(year, date):
    if not (year == cur_year and date.lstrip('0') == cur_date):
        old_filename = file_format.format(year, date.lstrip("0"))
        return pd.read_csv(old_filename)

    assert(year == cur_year and date.lstrip('0') == cur_date)
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })

    process.crawl(BaseballPressSpider)
    process.start()  # the script will block here until the crawling is finished

    print('\n'*6)
    return pd.read_csv(filename)


if __name__ == '__main__':
    run(cur_year, cur_date)
