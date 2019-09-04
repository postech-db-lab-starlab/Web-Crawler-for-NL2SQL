# Web-Crawler-for-NL2SQL


### Environment
1.  Create Python 3 virtual environment.

        python3 -m venv myvenv
        source myvenv/bin/activate

2.  Install the required dependencies.

        pip install -r requirements.txt


### How to run
This program requires 3 arguments.

1.  component name: url\_queue / web\_downloader / parser / sql\_extractor / table\_extractor / nl\_extractor
2.  input file type: sql / list
3.  input file name


Component name
1.  url\_queue: It executes crawling using Google Search. You should use filename.
2.  web\_downloader: It executes crawling with the ouputs of the url\_queue.
3.  parser: It parses a html and filters the html with content keywords.
4.  sql\_extractor: It extracts sql from the output of the parser and filters the html which doesn't have any SQLs.
5.  table\_extractor: It extracts tables from the output of the sql\_extractor.
6.  nl\_extractor: It extracts tables from htmls which not filtered.


Input file type
1.  sql: you can use sql as an input. (ex. select id from url\_info;)
2.  list: you can use list as an input
        (ex. In file...
            0
            1
            3
        )


Input file name

In the file, there is a list or a sql as an input.

1.  url\_queue

    It needs keywords
    
    - Example for sql: 

            select content form topic\_keywords;

    - Example for file:

            SQL
            select
            SQL+where+from

2.  web\_downloader, parser, sql\_extractor, table\_extractor, nl\_extractor 

    It needs ids of url.

    - Example for sql: 

            select id form url\_ids;

    - Example for file:

            0
            1
            3

###Test
You can test with the following commands

1. python web\_crawler.py url\_queue sql topic\_keywords.sql
2. python web\_crawler.py url\_queue list topic\_keywords.list
3. python web\_crawler.py web\_downloader sql url\_ids.sql
4. python web\_crawler.py web\_downloader list url\_ids.list
