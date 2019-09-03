# Web-Crawler-for-NL2SQL


Environments
    - python3


This program requires 3 arguments.
    - component name: url\_queue / web\_downloader / parser / sql\_extractor / table\_extractor / nl\_extractor
    - input file type: sql / list
    - input file name


Components
    - url\_queue: It executes crawling using Google Search. You should use filename.
    - web\_downloader: It executes crawling with the ouputs of the url\_queue.
    - parser: It parses a html and filters the html with content keywords.
    - sql\_extractor: It extracts sql from the output of the parser and filters the html which doesn't have any SQLs.
    - table\_extractor: It extracts tables from the output of the sql\_extractor.
    - nl\_extractor: It extracts tables from htmls which not filtered.


Input file type
    - sql: you can use sql as an input. (ex. select id from url\_info;)
    - list: you can use list as an input
        (ex. In file...
            0
            1
            3
        }


File name: In the file, there is a list or a sql as an input.
    - url\_queue: It needs keywords
        - Example for sql: select content form topic\_keywords;
        - Example for file:
            SQL
            select
            SQL+where+from
    - web\_downloader, parser, sql\_extractor, table\_extractor, nl\_extractor needs ids of url.
        - Example for sql: select id form url\_ids;
        - Example for file:
            0
            1
            3


You can test with the following commands
    1. python web\_crawler.py url\_queue sql topic\_keywords.sql
    2. python web\_crawler.py url\_queue list topic\_keywords.list
    3. python web\_crawler.py web\_downloader sql url\_ids.sql
    4. python web\_crawler.py web\_downloader list url\_ids.list

