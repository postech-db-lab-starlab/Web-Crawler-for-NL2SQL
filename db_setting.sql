create table topic_keywords(id serial primary key, content varchar(100));

create table url_info(id serial primary key, status integer);
create table url_content(url_id integer references url_info(id), content varchar(1000));
create table html_content(url_id integer references url_info(id), content text);

create table candidate_info(id serial primary key, url_id integer references url_info(id), position integer, status integer);
create table candidate_content(candidate_id integer references candidate_info(id), content text);

create table sql_info(id serial primary key, url_id integer references url_info(id), position integer);
create table sql_content(sql_id integer references sql_info(id), content text);

create table nl_info(id serial primary key, url_id integer references url_info(id), position integer);
create table nl_content(nl_id integer references nl_info(id), content text);

create table table_info(id serial primary key, url_id integer references url_info(id));
