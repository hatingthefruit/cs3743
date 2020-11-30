#!/usr/bin/python3

import random
import json
import sqlite3
from loremipsum import get_sentence

meta = json.load(open("gutenberg-metadata.json"))

conn = sqlite3.connect("app.db")
dbCursor = conn.cursor()

for book in range(100):
    bookNum = random.randrange(500)
    book = meta[str(bookNum)]
    isbn = f"{bookNum: 010}"
    try:
        title = book["title"][0]
    except:
        title = book["title"]
    try:
        language = book["language"][0]
    except:
        language = book["language"]
    try:
        author = book["author"][0]
    except:

        author = book["author"]
    try:
        subject = book["subject"][0]
    except:
        subject = book["subject"]
    command = f"insert into books (isbn, btitle, bauthor, bsubject, blanguage) values ('{isbn}', '{title}', '{author}', '{subject}', '{language}');"
    try:
        dbCursor.execute(command)

        conn.commit()
    except sqlite3.IntegrityError:
        print("Isbn already exists")
    except:
        print(command)"

updates = dbCursor.execute("select * from books where dds is null;").fetchall()

for book in updates:
    dds1 = random.randrange(100, 900, 100)
    dds2 = random.randrange(1000)
    ddsStr = f"{dds1}.{dds2}"
    print(ddsStr)
    #dbCursor.execute("update books set dds=%s;" % (ddsStr))

books = dbCursor.execute(
    "select isbn from books b where b.isbn not in (select s.isbn from stores_b s);").fetchall()

for isbn in updates:
    print(isbn)

bids = ["DTN", "WES", "EAS", "CEN"]

for book in books:
    for i in range(random.randrange(1, 3)):
        dbCursor.execute(
            f"insert into stores_b (isbn, bindex, bid) values ('{book[0]}', {i}, '{bids[random.randrange(3)]}');")


pnames = ["ABSTRACTS OF FOLKLORE STUDIES",
          "AMERICAN DIALECT SOCIETY. PUBLICATIONS", "AMERICAN LITERATURE"]
months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
years = [2016, 2017, 2018, 2019, 2020]

for name in pnames:
    for month in months:
        for year in years:
            dbCursor.execute(
                f"Insert into periodicals (pname, pedition, pgenre, ptype, dds, psubject) values ('{name}', '{month + str(year)}', 'American Lit.', 'magazine', '200.10', 'American Lit.')")

periods = dbCursor.execute(
    "select pname, pedition from periodicals ;").fetchall()
bids = ["DTN", "WES", "EAS", "CEN"]

for period in periods:
    for bid in bids:
        try:
            dbCursor.execute(
                f"insert into stores_p (pname, pedition, bid) values ('{period[0]}', '{period[1]}', '{bid}');")
        except:
            print("Had an exception")

books = dbCursor.execute("Select isbn, bindex from stores_b;").fetchmany(20)
unames = ['user1', 'user2']

for each in books:
    name = unames[random.randrange(0, 1)]
    dbCursor.execute(
        f"Insert into checked_out (uname, isbn, bindex, due) values ('{name}', '{each[0]}', '{each[1]}', '2020-dec-13');")
conn.commit()
conn.close()
