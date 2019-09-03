import sys
import json
import psycopg2
from bs4 import BeautifulSoup
import random
import time
from datetime import timedelta, date
from itertools import chain, combinations
import requests

class web_manager:
    def __init__(self):
        pass
    def request(self, url):
        try:
            return requests.get(url).text
        except:
            return None

class conf_manager:
    confs = {}
    def __init__(self):
        pass
    def read_file(self, fname):
        with open(fname) as f:
            lines = f.readlines()
            for line in lines:
                attrs = line.split(':')
                if len(attrs) != 2:
                    return False
                self.confs[attrs[0].strip()] = attrs[1].strip().split('#')[0].strip()
            return True
        return False


class interface_manager:
    def __init__(self):
        pass

    def sql2infos(self, dm, fname):
        with open(fname) as f:
            lines = f.readlines()
            stmt = ' '.join(lines)
            return dm.fetch_all(stmt)
        return None       

    def list2infos(self, fname):
        urlinfos = []
        with open(fname) as f:
            lines = f.readlines()
            for line in lines:
                urlinfos.append([line])
            return urlinfos
        return None

       
class db_manager:
    host, dbname, user, port, passwd = "", "", "", "", ""
    conn, curs = None, None
    table_db_dir = ""
    def __init__(self):
        pass

    def connect_postgres(self, host, dbname, user, port, passwd):
        self.host, self.dbname, self.user, self.port = str(host), str(dbname), str(user), str(port)
        self.passwd = str(passwd)
        conn_string = "host='%s' dbname='%s' user='%s' port='%s'" % (self.host, self.dbname, self.user, self.port)
        if len(self.passwd) > 0:
            conn_string += " password='%s'" % (self.passwd)
        self.conn = psycopg2.connect(conn_string)
        self.curs = self.conn.cursor()
        print("Successful connection to db")

    def connect_postgres_with_conf(self, confs):
        self.connect_postgres(confs['psql/host'], confs['psql/dbname'], confs['psql/user'], confs['psql/port'], confs['psql/passwd'])
    def connect_table_db(self, confs):
        self.table_db_dir = confs['tabledb/dir']

    def connect(self, confs):
        self.connect_postgres_with_conf(confs)
        self.connect_table_db(confs)

    def fetch_all(self, stmt):
        self.curs.execute(stmt)
        return self.curs.fetchall()  
    
    def execute(self, stmt):
        try:
            self.curs.execute(stmt)
        except:
            self.conn.rollback()

    def insert(self, stmt):
        try:
            self.curs.execute(stmt)
            return self.curs.fetchone()[0]
        except:
            return -1
    
    def insert_table(self, tid, table):
        dbname = "%s/%s" % (self.table_db_dir, str(tid))
        with open(dbname, 'w') as f:
            f.write(table.to_json())

    def commit(self):
        self.conn.commit()

    def fetch_table(self, tid):
        fname = "%s/%s" % (self.table_db_dir, str(tid))
        with open(fname) as f:
            try:
                return json.load(f)
            except:
                return None
        return None

    def update_url_status(self, uid, status):
        stmt = "update url_info set status = %s where id = %s" % (str(status), str(uid))
        self.curs.execute(stmt)

import nltk
from nltk.tokenize import sent_tokenize
import inflection
import re

class url_queue:

    min_interval_time, max_interval_time = None, None
    min_date, max_date, interval_date = None, None, None

    def __init__(self, confs):
        self.max_interval_time = int(confs['url_queue/max_interval_time'])
        self.min_interval_time = int(confs['url_queue/min_interval_time'])
        date_info = confs['url_queue/min_date'].split('-')
        self.min_date = date(int(date_info[0]), int(date_info[1]), int(date_info[2]))
        date_info = confs['url_queue/max_date'].split('-')
        self.max_date = date(int(date_info[0]), int(date_info[1]), int(date_info[2]))
        self.interval_date = int(confs['url_queue/interval_date'])

    def make_google_query(self, keyword, date_range):
        url = 'https://www.google.co.kr/search?q=%s&sa=N&filter=0&num=100' % (keyword.strip())
        if date_range is not None:
            url += '&tbs=cdr%3A1%2Ccd_min%3A{min_month}%2F{min_day}%2F{min_year}%2Ccd_max%3A{max_month}%2F{max_day}%2F{max_year}'.format(**date_range)
        url = url.replace('\n', '')
        return url

    def extract_google_query(self, html, page):
        soup = BeautifulSoup(html, "lxml")
        links = soup.find_all('a')
        for link in links:
            if str(page + 1) == link.text:
                return 'https://www.google.co.kr' + link.get('href')
        return None

    def extract_url_list(self, html):
        soup = BeautifulSoup(html, "lxml")
        result = []
        for link in soup.select('div[class="g"] > h3[class="r"] > a[href]'):
            result.append(link.attrs['href'])
        return result

    def inverse_date_range(self):
        date_range = {
            'max_year': None,
            'max_month': None,
            'max_day': None,
            'min_year': self.max_date.year,
            'min_month': self.max_date.month,
            'min_day': self.max_date.day,
        }
        for n in range(int((self.max_date - self.min_date).days / self.interval_date)):
            date_range['max_year'] = date_range['min_year']
            date_range['max_month'] = date_range['min_month']
            date_range['max_day'] = date_range['min_day']
            tmp = self.max_date - timedelta((n+1) * self.interval_date)
            date_range['min_year'] = tmp.year
            date_range['min_month'] = tmp.month
            date_range['min_day'] = tmp.day
            yield date_range

    def insert_url(self, dm, url):
        s = url.find("http")
        e = url.find("&sa=U&ved=0ah")
        if s == -1:
            return
        url = url[s:e]
        if len(url) < 5:
            return
        url = url.strip().replace("'", "''")
        stmt = "select id from url_info, url_content where url_info.id = url_content.url_id and url_content.content = '%s';" % (url)
        if len(dm.fetch_all(stmt)) > 0:
            return
        stmt = "insert into url_info(status) values(0) returning id;"
        uid = dm.insert(stmt)
        stmt = "insert into url_content(url_id, content) values(%s,'%s');" % (uid, url)
        dm.execute(stmt)


    def powerset(self, iterable):
        xs = list(iterable)
        return chain.from_iterable(combinations(xs,n) for n in range(len(xs)+1))

    def execute(self, wm, dm, keywords):
        print(keywords)
        keywords = [item[0] for item in keywords]
        keyword_subsets = list(self.powerset(keywords))
        for keyword_subset in keyword_subsets:
            if len(keyword_subset) == 0:
                continue
            print(keyword_subset)
            keyword = '+'.join(list(keyword_subset))
            for date_range in self.inverse_date_range():
                page, google_query = 1, self.make_google_query(keyword, date_range)
                while google_query is not None:
                    html = wm.request(google_query)
                    if html is None: break
                    urls = self.extract_url_list(html)
                    for url in urls:
                        self.insert_url(dm, url)
                    dm.commit()
                    print("page: %d, urls: %d" % (page, len(urls)))
                    page, google_query = page + 1, self.extract_google_query(html, page)
                    interval = random.randrange(self.min_interval_time, self.max_interval_time)
                    print("waiting.. %d seconds" % (interval))
                    time.sleep(interval)

class web_downloader():

    def __init__(self, confs):
        pass

    def get_url(self, dm, urlinfo):
        stmt = "select content from url_info, url_content where url_info.id = %s and url_info.id = url_content.url_id and url_info.status = 0 order by url_info.id;" % (urlinfo[0])
        try:
            return dm.fetch_all(stmt)[0][0]
        except:
            return None

    def filter_url(self, dm, urlinfo):
        dm.update_url_status(urlinfo[0], -1)

    def filtering(self, html):
        html = html.lower()
        if html.find('select') == -1 or html.find('from') == -1:
            return True
        return False

    def insert_html(self, dm, urlinfo, html):
        stmt = "insert into html_content(url_id, content) values(%s, '%s')" % (urlinfo[0], html.replace("'", "''"))
        dm.execute(stmt)

    def execute(self, wm, dm, urlinfos):
        cnt, tcnt = 0,0
        for urlinfo in urlinfos:
            tcnt += 1
            url = self.get_url(dm, urlinfo)
            if url is None:
                continue
            html = wm.request(url)
            if html is None or self.filtering(html):
                self.filter_url(dm, urlinfo)
                continue
            try:
                self.insert_html(dm, urlinfo, html)
            except:
                dm.update_url_status(urlinfo[0], -1)
            cnt += 1
            dm.update_url_status(urlinfo[0], 1)
            dm.commit()
            print("cnt/total cnt: %d / %d" % (cnt, tcnt))
        dm.commit()

class parser:

    def __init__(self, confs):
        self.tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
        self.extracted_tags = confs['parser/extracted_tags'].split(',')
        self.unwraped_tags = confs['parser/unwraped_tags'].split(',')
        self.space_tags = confs['parser/space_tags'].split(',')
        self.enter_tags = confs['parser/enter_tags'].split(',')
        self.enter_delim = confs['parser/enter_delimiter']
        self.content_filter_keywords = confs['parser/content_filter_keywords'].split(',')

    def extract_tag(self, soup):
        for tag in self.extracted_tags:
            try:
                [x.extract () for x in soup.find_all(tag)]
            except:
                continue
    
    def unwrap_tag(self, soup):
        for tag in self.unwraped_tags:
            try:
                [x.unwrap () for x in soup.find_all(tag)]
            except:
                continue

    def space_tag(self, html):
        for tag in self.space_tags:
            reg = "<(/)?(" + tag + ")(\\s[a-zA-Z]*=[^>]*)?(\\s)*(/)?>"
            html = re.sub(reg, ' ', html)
        return html

    def enter_tag(self, html):
        for tag in self.enter_tags:
            reg = "<(/)?(" + tag + ")(\\s[a-zA-Z]*=[^>]*)?(\\s)*(/)?>"
            html = re.sub(reg, self.enter_delim, html)
        return html

    def preprocess_html(self, html):
        html = self.space_tag(html)
        html = self.enter_tag(html)
        soup = BeautifulSoup(html, 'lxml')
        self.extract_tag(soup)
        self.unwrap_tag(soup)
        text = soup.get_text()
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        text = re.sub("( )+", " ", text)
        return text

    def extract_candidates(self, paragraph):
        candidates = []
        for part in self.tokenizer.tokenize(paragraph):
            part = part.replace('; ', '; ' + self.enter_delim)
            part = part.replace(': ', ': ' + self.enter_delim)
            for splitted in part.split(self.enter_delim):
                candidates.append(splitted.strip())
        return candidates

    def extract_paragraphs(self, text):
        return text.split(self.enter_delim)

    def insert_candidate(self, dm, uid, position, content, status):
        stmt = "insert into candidate_info(url_id, position, status) values (%s, %s, %s) returning id;" % (str(uid), str(position), str(status))
        cid = dm.insert(stmt)
        content = content.replace("'", "''")
        stmt = "insert into candidate_content(candidate_id, content) values(%s,'%s');" % (str(cid), content.replace("'", "''"))
        dm.execute(stmt)

    def check_content(self, candidate):
        candidate = candidate.lower()
        for keyword in self.content_filter_keywords:
            if candidate.find(keyword) > -1:
                return 1
        return -1

    def content_filtering(self, candidates):
        result = []
        final_status = False
        for candidate in candidates:
            status = self.check_content(candidate)
            result.append((candidate, status))
            if status == 1:
                final_status = True
        if final_status:
            return result
        return []

    def get_html(self, dm, urlinfo):
        stmt = "select content from url_info, html_content where url_info.id = html_content.url_id and url_info.status = 1 and url_info.id = %s" % (urlinfo[0])
        try:
            return dm.fetch_all(stmt)[0][0]
        except:
            return None
                
    def execute(self, dm, urlinfos):
        cnt, tcnt = 0, 0
        for urlinfo in urlinfos:
            tcnt += 1
            html = self.get_html(dm, urlinfo)
            if html is None:
                continue
            html = self.preprocess_html(html)
            paragraphs = self.extract_paragraphs(html)            
            candidates = []
            for paragraph in paragraphs:
                candidates += self.extract_candidates(paragraph)
            position = 0
            for (candidate, status) in self.content_filtering(candidates):
                self.insert_candidate(dm, urlinfo[0], position, candidate, status)
                position += 1
            if position == 0:
                dm.update_url_status(urlinfo[0], -2)
            else:
                dm.update_url_status(urlinfo[0], 2)
                cnt += 1
                print("cnt/total cnt: %d / %d" % (cnt, tcnt))
        dm.commit()

from antlr4 import *
sys.path.insert(0, './antlr4')
from SQLiteLexer import SQLiteLexer
from SQLiteParser import SQLiteParser
from SQLiteListener import SQLiteListener

class sql_extractor:
    def __init__(self, confs):
        self.keywords = ['insert', 'select', 'delete', 'create']
        pass

    def extract_start(self, text):
        minIdx = -1
        for keyword in self.keywords:
            idx = text.find(keyword)
            if minIdx == -1 or (idx >= 0 and minIdx > idx): minIdx = idx
        return minIdx

    def extract_end(self, text, sql):
        sql = sql.strip()
        if len(sql) == 0: return 1
        i, idx, spaces = 0, 0, [' ', '\n', '\r']
        for space in spaces:
            sql = sql.replace(space, '')
        while i < len(sql):
            if len(text) <= idx: break
            if text[idx] not in spaces: i += 1
            idx += 1
        return idx + 1

    def extract_sql(self, text):
        lexer = SQLiteLexer(InputStream(text))
        stream = CommonTokenStream(lexer)
        parser = SQLiteParser(stream)
        try:
            sql_stmt_list = parser.parse().sql_stmt_list()
            sql_stmt = sql_stmt_list[0]
            return sql_stmt.getText()
        except:
            return ""

    def extract(self, text):
        if len(text) < 2: return (text, [])
        lowText = text.lower()
        sqls = []
        idxB = 0
        newText = ''
        length = len(lowText)
        while idxB < length - 1:
            idxS = self.extract_start(lowText[idxB:])
            if idxS >= 0:
                newText += text[idxB:idxB+idxS]
                idxB += idxS
                sql = self.extract_sql(text[idxB:])
                idxE = self.extract_end(text[idxB:], sql)
                if idxE > 1: 
                    sqls.append(text[idxB:idxB+idxE])
                    newText += '<sql:' + str(len(sqls)) + '>'
                else: 
                    newText += text[idxB:idxB+idxE]
                idxB += idxE
            else:
                newText += text[idxB:]
                break
        return (newText, sqls)
     
    def get_candidates(self, dm, urlinfo):
        stmt = "select candidate_info.id, candidate_content.content, candidate_info.position from url_info, candidate_info, candidate_content where candidate_info.status = 1 and candidate_info.id = candidate_content.candidate_id and url_info.id = candidate_info.url_id and url_info.status = 2 and candidate_info.url_id = %s;" % (urlinfo[0])
        return dm.fetch_all(stmt)

    def insert_sql(self, dm, uid, position, content):
        stmt = "insert into sql_info(url_id, position) values(%s, %s) returning id;" % (str(uid), str(position))
        sid = dm.insert(stmt)
        stmt = "insert into sql_content(sql_id, content) values(%s, '%s');" % (str(sid), content.replace("'", "''"))
        dm.execute(stmt)
  
    def filtering(self, candidate):
        candidate = candidate.lower()
        s = candidate.find('select')
        if s < -1:
            return True
        e = candidate.find('from')
        if e < s:
            return True
        return False
   
    def cfg_filter_url(self, dm, urlinfo):
        dm.update_url_status(urlinfo[0], -3)

    def execute(self, dm, urlinfos):
        cnt, tcnt = 0, 0
        for urlinfo in urlinfos:
            tcnt += 1
            result = []
            for candidate in self.get_candidates(dm, urlinfo):
                if self.filtering(candidate[1]):
                    continue
                (newText, sqls) = self.extract(candidate[1])
                print(sqls)
                for sql in sqls:
                    result.append((urlinfo[0], candidate[2], sql.strip()))
            if len(result) == 0:
                self.cfg_filter_url(dm, urlinfo)
                dm.commit()
                continue
            for (uid, position, content) in result:
                self.insert_sql(dm, uid, position, content)
            dm.update_url_status(urlinfo[0], 3)
            dm.commit()
            cnt += 1
            print("cnt/total cnt: %d / %d" % (cnt, tcnt))
        dm.commit()
        
import pandas as pd
import html5lib
import requests

class table_extractor:
    def __init__(self, confs):
        pass

    def update_status(self, dm, uid, status):
        stmt = "update url_info set status = %s where id = %s;" % (str(status), str(uid))
        dm.execute(stmt)
        
    def insert_table(self, dm, uid, table):
        stmt = "insert into table_info(url_id)  values(%s) returning id;" % (str(uid))
        tid = dm.insert(stmt)
        dm.insert_table(tid, table)

    def extract_table(self, url):
        try:
            return pd.read_html(url, header=0)
        except:
            return None

    def get_url(self, dm, urlinfo):
        stmt = "select content from url_info, url_content where url_info.id = url_content.url_id and url_id = %s and url_info.status = 3;" % (urlinfo[0])
        try:
            return dm.fetch_all(stmt)[0][0]
        except:
            return None

    def execute(self, dm, urlinfos):
        cnt, tcnt = 0, 0
        for urlinfo in urlinfos:
            tcnt += 1
            url = self.get_url(dm, urlinfo)
            if url is None:
                continue
            tables = self.extract_table(url)        
            if tables is None:
                self.update_status(dm, urlinfo[0], -4)
                continue
            for table in tables:
                self.insert_table(dm, urlinfo[0], table)
                self.update_status(dm, urlinfo[0], 4)
            cnt += 1
            print("cnt/total cnt: %d / %d" % (cnt, tcnt))
        dm.commit() 

class nl_extractor:
    def __init__(self, confs):
        pass

    def insert_nl(self, dm, uid, position, content):
        stmt = "insert into nl_info(url_id, position) values(%s, %s) returning id;" % (str(uid), str(position))
        sid = dm.insert(stmt)
        stmt = "insert into nl_content(nl_id, content) values(%s, '%s');" % (str(sid), content.replace("'", "''"))
        dm.execute(stmt)
        pass 
    
    def get_candidates(self, dm, urlinfo):
        stmt = "select candidate_info.id, candidate_content.content, candidate_info.position from url_info, candidate_info, candidate_content where candidate_info.status = -1 and candidate_info.id = candidate_content.candidate_id and url_info.id = candidate_info.url_id and url_info.status = 4 and candidate_info.url_id = %s;" % (urlinfo[0])
        return dm.fetch_all(stmt)

    def extract(self, candidate):
        return [candidate]

    def execute(self, dm, urlinfos):
        cnt, tcnt = 0, 0
        for urlinfo in urlinfos:
            tcnt += 1
            result = []
            for candidate in self.get_candidates(dm, urlinfo):
                nls = self.extract(candidate[1])
                for nl in nls:
                    result.append((urlinfo[0], candidate[2], nl.strip()))
            if len(result) == 0:
                dm.update_url_status(urlinfo[0], -5)
                continue
            for (uid, position, content) in result:
                self.insert_nl(dm, uid, position, content)
            dm.update_url_status(urlinfo[0], 5)
            cnt += 1
            print("cnt/total cnt: %d / %d" % (cnt, tcnt))
        dm.commit()

if __name__ == '__main__':
    dm, cm = db_manager(), conf_manager()
    im, wm = interface_manager(), web_manager()
    if cm.read_file('./web_crawler.conf') == False:
        print('No web_crawler.conf file')
        pass
    dm.connect(cm.confs)
    if (sys.argv[1] == 'url_queue'):
        print('Crawling urls using Google Search')
        extractor = url_queue(cm.confs)
        fname = sys.argv[3]
        if (sys.argv[2] == 'list'):
            print('..with keyword list: ', fname)
            extractor.execute(wm,dm,im.list2infos(fname))
        elif (sys.argv[2] == 'sql'):
            print('..with sql: ', fname)
            extractor.execute(wm,dm,im.sql2infos(dm,fname))
        else:
            print('Wrong option. Choose list or sql')
    elif(sys.argv[1] == 'web_downloader'):
        print('Web downloading...')
        extractor = web_downloader(cm.confs)
        fname = sys.argv[3]
        if (sys.argv[2] == 'list'):
            print('..with URL id list: ', fname)
            extractor.execute(wm,dm,im.list2infos(fname))
        elif (sys.argv[2] == 'sql'):
            print('..with sql: ', fname)
            extractor.execute(wm,dm,im.sql2infos(dm,fname))
        else:
            print('Wrong option. Choose list or sql')
    elif(sys.argv[1] == 'parser'):
        print('Parsing and content filtering...')
        extractor = parser(cm.confs)
        fname = sys.argv[3]
        if (sys.argv[2] == 'list'):
            print('..with URL id list: ', fname)
            extractor.execute(dm,im.list2infos(fname))
        elif (sys.argv[2] == 'sql'):
            print('..with sql: ', fname)
            extractor.execute(dm,im.sql2infos(dm,fname))
        else:
            print('Wrong option. Choose list or sql')
    elif(sys.argv[1] == 'sql_extractor'):
        print('Extracting SQL and fitering...')
        extractor = sql_extractor(cm.confs)
        fname = sys.argv[3]
        if (sys.argv[2] == 'list'):
            print('..with URL id list: ', fname)
            extractor.execute(dm,im.list2infos(fname))
        elif (sys.argv[2] == 'sql'):
            print('..with sql: ', fname)
            extractor.execute(dm,im.sql2infos(dm,fname))
        else:
            print('Wrong option. Choose list or sql')
    elif(sys.argv[1] == 'table_extractor'):
        print('Extracting table...')
        extractor = table_extractor(cm.confs)
        fname = sys.argv[3]
        if (sys.argv[2] == 'list'):
            print('..with URL id list: ', fname)
            extractor.execute(dm,im.list2infos(fname))
        elif (sys.argv[2] == 'sql'):
            print('..with sql: ', fname)
            extractor.execute(dm,im.sql2infos(dm,fname))
        else:
            print('Wrong option. Choose list or sql')
    elif(sys.argv[1] == 'nl_extractor'):
        print('Extracting nl...')
        extractor = nl_extractor(cm.confs)
        fname = sys.argv[3]
        if (sys.argv[2] == 'list'):
            print('..with URL id list: ', fname)
            extractor.execute(dm,im.list2infos(fname))
        elif (sys.argv[2] == 'sql'):
            print('..with sql: ', fname)
            extractor.execute(dm,im.sql2infos(dm,fname))
        else:
            print('Wrong option. Choose list or sql')
    else:
            print('Wrong component')
     
