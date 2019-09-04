python3 ./web_crawler.py web_downloader sql sqls/web_downloader.sql;
python3 ./web_crawler.py parser sql sqls/parser.sql;
python3 ./web_crawler.py sql_extractor sql sqls/sql_extractor.sql;
python3 ./web_crawler.py table_extractor sql sqls/table_extractor.sql;
python3 ./web_crawler.py nl_extractor sql sqls/nl_extractor.sql
