from flask import Flask,request,url_for,session,render_template,jsonify,flash,redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session,sessionmaker
from logr import login_required
import os,json
from werkzeug.security import check_password_hash,generate_password_hash

import requests


app=Flask(__name__,template_folder="template")

if not "postgres://swgbwjngevunld:0ca53e5f8a2ace6a543273836b975bb733862f5374aaddfe2ce7659db126afca@ec2-52-44-55-63.compute-1.amazonaws.com:5432/dc2tof4iv20q6i":
    raise RuntimeError("DATABASE_URL is not set")

app.config["SESSION_PERMANENT"]=False
app.config["SESSION_TYPE"]="filesystem"
app.config["SECRET_KEY"]="thisISsecret"
Session(app)

engine=create_engine("postgres://swgbwjngevunld:0ca53e5f8a2ace6a543273836b975bb733862f5374aaddfe2ce7659db126afca@ec2-52-44-55-63.compute-1.amazonaws.com:5432/dc2tof4iv20q6i")
db=scoped_session(sessionmaker(bind=engine))

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        if session["user_id"]:
            session.clear()
    except:
        pass

    username = request.form.get("username")

    if request.method == "POST":

        if not request.form.get("username"):
            return render_template("error.html", message="must provide username")

        elif not request.form.get("password"):
            return render_template("error.html", message="must provide password")

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": username})

        result = rows.fetchone()

        if result == None or not check_password_hash(result[2], request.form.get("password")):
            return render_template("error.html", message="invalid username and/or password")

        session["user_id"] = result[0]
        session["user_name"] = result[1]
        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    session.clear()

    if request.method == "POST":

        if not request.form.get("username"):
            return render_template("error.html", message="must provide username")

        userCheck = db.execute("SELECT * FROM users WHERE username = :username",
                               {"username": request.form.get("username")}).fetchone()

        if userCheck:
            return render_template("error.html", message="username already exist")

        elif not request.form.get("password"):
            return render_template("error.html", message="must provide password")

        elif not request.form.get("confirmation"):
            return render_template("error.html", message="must confirm password")

        elif not request.form.get("password") == request.form.get("confirmation"):
            return render_template("error.html", message="passwords didn't match")

        # Hash user's password to store in DB
        hashedPassword = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        # Insert register into DB
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)",
                   {"username": request.form.get("username"),
                    "password": hashedPassword})

        # Commit changes to database
        db.commit()

        flash("account created","info")

        # Redirect user to login page
        return redirect('login')

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/search")
@login_required
def search():

    if not request.args.get("book"):
        return render_template("error.html",message="invalid search u must give some input")

    query="%"+request.args.get("book")+"%"

    query=query.title()
    print(query)
    rows=db.execute("select isbn,title,author,year from books where \
                    isbn like :query or \
                    title like :query or \
                    author like :query limit 15",{"query":query})

    if rows.rowcount == 0:
        return render_template("error.html",message="no such book available.")

    """
    for book in rows:
        print(book)
    """

    return render_template("results.html",books=rows)

@app.route("/book/<isbn>",methods=["GET","POST"])
@login_required
def book(isbn):
    row = db.execute("select isbn,title,author,year from books where isbn= :isbn",
                     {
                         "isbn": isbn
                     })
    book_info = row.fetchall()

    key = " lVAfqmTezMQO4iFgVI6hOw"

    query = requests.get("https://www.goodreads.com/book/review_counts.json",
                         params={"access_key": " lVAfqmTezMQO4iFgVI6hOw", "isbns": isbn})

    response = query.json()

    response = response['books'][0]

    book_info.append(response)

    row = db.execute("select id from books where isbn= :isbn", {
        "isbn": isbn
    })

    book = row.fetchone()
    book = book[0]

    results = db.execute("SELECT users.username, comments, rating, \
                                       to_char(time, 'DD Mon YY - HH24:MI:SS') as time \
                                       FROM users \
                                       INNER JOIN reviews \
                                       ON users.id = reviews.user_id \
                                       WHERE book_id = :book \
                                       ORDER BY time",
                         {"book": book})

    reviews = results.fetchall()

    if request.method=="POST":
        curr_user=session["user_id"]

        rating=request.form.get("rating")
        comment=request.form.get("comment")

        row=db.execute("select id from books where isbn= :isbn",{"isbn":isbn})

        book_id=row.fetchone()
        book_id=book_id[0]

        row1=db.execute("select * from reviews where user_id= :user_id and book_id= :book_id",
                        {
                            "user_id": curr_user,
                            "book_id" : book_id
                        })

        if row1.rowcount == 1:
            flash("bsdk ek baar ho gya h","info")
            return render_template("book.html", bookInfo=book_info, reviews=reviews)
            #return redirect('/book/'+isbn) not working flash here
        rating=int(rating)

        db.execute("insert into reviews(user_id,book_id,comments,rating) values \
                   (:user_id,:book_id,:comment,:rating)",
                   {
                       "user_id" : curr_user,
                       "book_id" : book_id,
                       "comment" : comment,
                       "rating"  : rating
                   })

        db.commit()
        results = db.execute("SELECT users.username, comments, rating, \
                                               to_char(time, 'DD Mon YY - HH24:MI:SS') as time \
                                               FROM users \
                                               INNER JOIN reviews \
                                               ON users.id = reviews.user_id \
                                               WHERE book_id = :book \
                                               ORDER BY time",
                             {"book": book})

        reviews = results.fetchall()
        flash('review submitted','info')

        return render_template("book.html", bookInfo=book_info, reviews=reviews)

    else:
        return render_template("book.html", bookInfo=book_info, reviews=reviews)






if __name__ == "__main__":
    app.debug=True
    app.run(use_reloader=True)