import scrapy

from scrapy import Selector, Request


class RotoguruSpider(scrapy.Spider):
    name = "rotoguru"
    allowed_domains = ["rotoguru1.com"]

    mapping = []

    for year in [2014, 2015]:
        for month in range(1, 13):
            for day in range(1, 32):
                # dk: draftkings, fd: fanduel, sf: star fantasy
                # dd: draftday
                for site in ['dk', 'fd', 'sf', 'dd']:
                    url = ("http://rotoguru1.com/cgi-bin/byday.pl?"
                           "date=%d%02d&game=%s&year=%d&scsv=1" %
                           (month, day, site, year))

                    mapping.append((month, day, year, site, url))

    def start_requests(self):
        for month, day, year, site, url in self.mapping:
            yield Request(url, callback=self.parse,
                          meta={'date': "%d%02d" % (month, day),
                                'year': year,
                                'site': site})

    def parse(self, response):
        hxs = Selector(response)
        csv_data = hxs.select("//a[@name='scsv']/following-sibling::p[1]")[0]
        rows = csv_data.extract().split('<br>\n')
        rows[0] = "Date;GID;MLB_ID;Name;Starter;Bat order;DK posn;DK pts;DK sal;Team;Oppt;dblhdr;Tm Runs;Opp Runs;Stat line"
        if rows[-1] == '</p>':
            del rows[-1]

        if len(rows) <= 1:
            return

        year = response.meta['year']
        date = response.meta['date']
        site = response.meta['site']
        filename = '%s/%d/playerInfo_%s.csv' % (site, year, date)
        with open(filename, 'wb') as f:
            f.write('\n'.join(rows))
