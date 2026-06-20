CREATE TABLE IF NOT EXISTS articles (
    id          INTEGER PRIMARY KEY,
    law_id      TEXT NOT NULL,
    law_title   TEXT NOT NULL,
    article_num TEXT NOT NULL,
    paragraph_num TEXT DEFAULT '',
    item_num    TEXT DEFAULT '',
    heading     TEXT DEFAULT '',
    text        TEXT NOT NULL,
    path        TEXT NOT NULL UNIQUE
);

CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    law_title,
    heading,
    text,
    content='articles',
    content_rowid='id',
    tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, law_title, heading, text)
    VALUES (new.id, new.law_title, new.heading, new.text);
END;

CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, law_title, heading, text)
    VALUES ('delete', old.id, old.law_title, old.heading, old.text);
END;

CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, law_title, heading, text)
    VALUES ('delete', old.id, old.law_title, old.heading, old.text);
    INSERT INTO articles_fts(rowid, law_title, heading, text)
    VALUES (new.id, new.law_title, new.heading, new.text);
END;

CREATE TABLE IF NOT EXISTS manifest (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
