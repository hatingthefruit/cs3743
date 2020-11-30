#!/usr/bin/python3

from flask import Flask, render_template, request, jsonify, url_for, redirect
import sqlite3

# Try to set up the scheduler to run fine updates and user status updates in the background
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    userUpdates = BackgroundScheduler(daemon=True)
    userUpdates.start()
except:
    print("Trouble importing scheduler; user update functionality will be disabled")
    userUpdates = False


app = Flask(__name__)
conn = sqlite3.connect("app.db")
dbCursor = conn.cursor()


# Function to update fines and user standing. This will be run daily by the background scheduler
def updateCustFines():
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()
    tempCursor.execute("""UPDATE CUSTOMERS
        SET CFINES = CFINES + 3 * (
        SELECT COUNT(C1.UNAME) COUNTS
        FROM CUSTOMERS C1 JOIN (
            SELECT *
            FROM CHECKED_OUT
            WHERE DUE < DATE('NOW', 'LOCALTIME')
        ) CO
        ON C1.UNAME=CO.UNAME GROUP BY C1.UNAME
        );""")
    tempConn.commit()
    print("updated user info")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/book/<isbn>")
def getBookInfo(isbn):
    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()

    # select the book for this page
    book = tempCursor.execute(
        f'SELECT * FROM BOOKS WHERE ISBN ="{isbn}";').fetchone()

    # Find the names of the branches and the number of the book available at each
    branches = tempCursor.execute(f"""SELECT B.BNAME, COUNT(*)
        FROM (
            SELECT *
            FROM STORES_B S JOIN BOOKS B ON S.ISBN = B.ISBN
        ) AS B_TO_P JOIN BRANCHES B ON B.BID=B_TO_P.BID
        WHERE B_TO_P.ISBN='{isbn}'
        GROUP BY B.BID, B_TO_P.ISBN;""").fetchall()
    return render_template("book.html", book=book, branches=branches)


@app.route("/branches")
def allBranches():
    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()

    # Get the names for each branch and a corresponding bid
    branches = tempCursor.execute(
        """SELECT BNAME, BID FROM BRANCHES;""").fetchall()
    return render_template("branches.html", branches=branches)


@app.route("/branches/<bid>")
def getBranchInfo(bid):

    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()

    # get the info about the current branch
    bidInfo = tempCursor.execute(f"""SELECT *
        FROM BRANCHES
        WHERE BID='{bid.upper()}';""").fetchone()
    # Get a list of all periodicals stored at this branch
    periodicals = tempCursor.execute(f"""SELECT DISTINCT PNAME
        FROM STORES_P
        WHERE BID='{bid}';""")
    return render_template("bid.html", bid=bidInfo, periodicals=periodicals)


@ app.route("/search", methods=['POST'])
def searchBooks():

    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()

    # Search for all the books by keyword in title based on the post request submitted
    items = tempCursor.execute(f"""SELECT * FROM BOOKS
    WHERE BTITLE LIKE '%{request.form["keyword"]}%' ORDER BY
    BTITLE;""").fetchall()

    # create a dictionary that stores the branches where each book is available, so we can pass this to the template renderer
    bids = {}
    for book in items:
        bids[book[0]] = tempCursor.execute(f"""SELECT B.BNAME
            FROM BRANCHES B
            WHERE EXISTS (
            SELECT *
            FROM STORES_B S
            WHERE S.ISBN='{book[0]}' AND S.BID=B.BID
            );""").fetchall()
    return render_template("search_book.html", items=items, keyword=request.form["keyword"], bids=bids)


@ app.route("/periodicals/bybranch")
def listPeriodicalsByBranch():

    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()

    # Get the branches, periodicals, and editions available per branch
    periodNames = tempCursor.execute(f"""SELECT B.BNAME, B_TO_P.PNAME, B_TO_P.PEDITION
        FROM (
        SELECT *
        FROM STORES_P S JOIN PERIODICALS P
        ON S.PNAME = P.PNAME AND S.PEDITION = P.PEDITION
        ) AS B_TO_P JOIN BRANCHES B ON B.BID=B_TO_P.BID;""").fetchall()
    return render_template("periodicalsbybranch.html", periodNames=periodNames)


@ app.route("/periodicals")
def listPeriodicals():

    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()

    # get all periodicals available in the database
    periodNames = tempCursor.execute(f"""SELECT DISTINCT PNAME
        FROM PERIODICALS
        ORDER BY PNAME;""").fetchall()
    return render_template("periodicals.html", periodNames=periodNames)


@ app.route("/periodicals/<pname>")
def getPerInfo(pname):

    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()
    # Get all the editions available for the current periodical name
    peditions = tempCursor.execute(f"""SELECT PEDITION
        FROM PERIODICALS
        WHERE PNAME='{pname}';""").fetchall()
    return render_template("pname.html", peditions=peditions, pname=pname)


@ app.route("/periodicals/<pname>/<pedition>")
def getPerEdition(pname, pedition):

    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()

    # Get the information about the current periodical edition from the database
    edition = tempCursor.execute(
        f"""SELECT * FROM PERIODICALS WHERE PNAME='{pname}' AND PEDITION='{pedition}';""").fetchone()
    # Get all the branches where this particular periodical edition can be found
    branches = tempCursor.execute(f"""SELECT B.BNAME
        FROM BRANCHES B
        WHERE EXISTS (
        SELECT *
        FROM STORES_P S
        WHERE S.PNAME='{pname}' AND S.PEDITION='{pedition}' AND
        S.BID=B.BID);""").fetchall()
    return render_template("pedition.html", branches=branches, edition=edition)


@ app.route("/customer/", methods=['POST', 'GET'])
def getCustomer():
    # Try to fetch the customer information requested by the user, or show the form if no request has been made
    if request.method == "POST":
        username = request.form["username"]
        return redirect(url_for('showCustInfo', username=username))
    else:
        return render_template("customer.html")


@ app.route("/customer/<username>")
def showCustInfo(username):
    # Redirect back to customer search if no customer name has been entered
    if username == "":
        return redirect(url_for("getCustomer"))

    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()

    tempCursor.execute("""UPDATE CUSTOMERS
        SET CSTANDING = CASE
        WHEN UNAME IN (
            SELECT DISTINCT C1.UNAME
            FROM CUSTOMERS C1 INNER JOIN (
                SELECT *
                FROM CHECKED_OUT
                WHERE DUE < DATE('NOW', 'LOCALTIME')
            ) CO ON C1.UNAME=CO.UNAME) THEN 'OVERDUE'
        ELSE 'GOOD'
        END;""")

    # Get the customer information for the current username
    custInfo = tempCursor.execute(
        f"""SELECT * FROM CUSTOMERS WHERE UNAME='{username}';""").fetchone()
    # redirect back to the search page if the customer does not exist
    if custInfo == None:
        return redirect(url_for("getCustomer"))

    # if the customer does exist, get all the book information from their checked out books
    books = tempCursor.execute(f"""SELECT *
        FROM (CHECKED_OUT C JOIN BOOKS B ON C.ISBN=B.ISBN)
        WHERE C.UNAME='{username}';""").fetchall()
    return render_template("username.html", username=username, books=books, custInfo=custInfo)


@app.route("/customer/renewall/<username>", methods=["POST"])
def renewAllBooks(username):
    # Redirect if the username is empty
    if username == "":
        return redirect(url_for("getCustomer"))

    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()
    # renew all books for the current customer and commit
    tempCursor.execute(f"""UPDATE CHECKED_OUT
            SET DUE=DATE(DUE, '+14 DAYS'), RENEWALS = RENEWALS - 1
            WHERE RENEWALS > 0 AND UNAME='{username}';""")
    tempConn.commit()
    # redirect back to customer page
    return redirect(url_for("showCustInfo", username=username))


@app.route("/customer/renew/<username>",  methods=["POST"])
def renewBooks(username):
    # redirect if the username is empty
    if username == "":
        return redirect(url_for("getCustomer"))

    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()
    # iterate through all isbns to renew
    for key in request.form.keys():
        # check boxes in html are of the format "renew {ISBN}". Check to make sure the current key is trying to renew a book
        if key.startswith("renew") and request.form[key] == 'on':
            # Renew the book with the current isbn and username
            tempCursor.execute(f"""UPDATE CHECKED_OUT
            SET DUE=DATE(DUE, '+14 DAYS'), RENEWALS = RENEWALS - 1
            WHERE RENEWALS > 0 AND UNAME='{username}' AND ISBN='{key[5:]}';""")
    # commit the database and then redirect back to customer info page
    tempConn.commit()
    return redirect(url_for("showCustInfo", username=username))


@app.route("/customer/pay/<username>", methods=["POST"])
def payFines(username):
    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()
    amount = request.form["amount"]
    tempCursor.execute(f"""UPDATE CUSTOMERS
        SET CFINES = CFINES - {float(amount)}
        WHERE UNAME='{username}';""")
    tempConn.commit()
    return redirect(url_for("showCustInfo", username=username))


@ app.route("/customer/update/<username>")
def updateCustInfo(username):
    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()
    custInfo = tempCursor.execute(
        f"""SELECT * FROM CUSTOMERS WHERE UNAME='{username}';""").fetchone()
    print(custInfo)
    return render_template("update.html", username=username, custInfo=custInfo)


@ app.route("/customer/update/handle/<username>", methods=['POST'])
def handleCustUpdate(username):
    # open connection to database
    tempConn = sqlite3.connect("app.db")
    tempCursor = tempConn.cursor()

    address = request.form['add1'] + ", " + request.form['add2']
    email = request.form['email']
    phone = request.form['phone']
    card = request.form['card']
    dob = request.form['dob']
    tempCursor.execute(f"""UPDATE CUSTOMERS
        SET CARD={int(card)}, EMAIL='{email}',
        CADDRESS='{address}', CDOB='{dob}', CPHONE={int(phone)}
        WHERE UNAME='{username}';""")
    tempConn.commit()
    return redirect(url_for('showCustInfo', username=username))


# Add user info update job to the scheduler
if userUpdates != False:
    userUpdates.add_job(updateCustFines, 'cron', day='*')
# start the webapp
app.run(debug=True)
