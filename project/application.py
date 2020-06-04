from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd


# Configure application
app = Flask(__name__)

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///survey.db")



@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    searches=db.execute("SELECT * FROM surveys ORDER BY views DESC")

    if request.method == "POST":


        surveyid= request.form.get("survId")
        surveys= db.execute("SELECT * FROM surveys WHERE id=:id", id=surveyid)

        questions = db.execute("SELECT * FROM questions WHERE surveyid=:surveyid", surveyid=surveyid)

        options = dict()


        for question in questions:
            choices= db.execute("SELECT * FROM options WHERE questionid=:questionid", questionid=question["id"])
            options[question["id"]]=choices

        return render_template("take.html",surveys=surveys, questions=questions, options=options)

    else:
        return render_template("homepage.html",searches=searches)

@app.route("/acc", methods=["GET", "POST"])
@login_required
def acc():
    searches=db.execute("SELECT * FROM surveys WHERE creatorid=:id ORDER BY views DESC",id=session["user_id"])

    if request.method == "POST":
        surveyid= request.form.get("survId")
        surveys= db.execute("SELECT * FROM surveys WHERE id=:id", id=surveyid)
        users = db.execute("SELECT * FROM users WHERE id=:id", id=session["user_id"])
        questions = db.execute("SELECT * FROM questions WHERE surveyid=:surveyid", surveyid=surveyid)

        options = dict()


        for question in questions:
            choices= db.execute("SELECT * FROM options WHERE questionid=:questionid", questionid=question["id"])
            options[question["id"]]=choices

        return render_template("view.html",surveys=surveys, questions=questions, options=options)
    else:
        users= db.execute("SELECT * FROM users WHERE id=:id", id=session["user_id"])
        return render_template("account.html",searches=searches, users=users)

@app.route("/views")
@login_required
def view():
    return render_template("view.html")

@app.route("/take", methods= ["GET","POST"])
@login_required
def take():

    if request.method =="POST":
        survey = request.form.get("survId")
        button = request.form.get("button")

        if button == "cancel" :
            searches=db.execute("SELECT * FROM surveys ORDER BY views DESC")
            return render_template("homepage.html",searches=searches)

        db.execute("UPDATE surveys SET views = views + 1 WHERE id=:surveyid",surveyid=survey)
        questions = db.execute("SELECT * FROM questions WHERE surveyid=:surveyid", surveyid=survey)

        for question in questions:
            choice  = request.form[str(question["id"])]
            db.execute("UPDATE options SET choicevalue = choicevalue + 1 WHERE id=:id", id=choice)

        searches=db.execute("SELECT * FROM surveys ORDER BY views DESC")
        return render_template("homepage.html",searches=searches)

    else:
        return render_template("take.html")

@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Allow user to change her password"""

    if request.method == "POST":

        # Ensure current password is not empty
        if not request.form.get("current_password"):
            return apology("must provide current password", 400)

        # Query database for user_id
        rows = db.execute("SELECT hash FROM users WHERE id = :user_id", user_id=session["user_id"])

        # Ensure current password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("current_password")):
            return apology("invalid password", 400)

        # Ensure new password is not empty
        if not request.form.get("new_password"):
            return apology("must provide new password", 400)

        # Ensure new password confirmation is not empty
        elif not request.form.get("new_password_confirmation"):
            return apology("must provide new password confirmation", 400)

        # Ensure new password and confirmation match
        elif request.form.get("new_password") != request.form.get("new_password_confirmation"):
            return apology("new password and confirmation must match", 400)

        # Update database
        hash = generate_password_hash(request.form.get("new_password"))
        rows = db.execute("UPDATE users SET hash = :hash WHERE id = :user_id", user_id=session["user_id"], hash=hash)

        # Show flash
        flash("Changed!")

    return render_template("change_password.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    if request.method == "POST":


        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect(url_for("index"))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect(url_for("index"))

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("name"):
            return apology("must provide name", 400)
        elif not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password and confirmation match
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        # hash the password and insert a new user in the database
        hash = generate_password_hash(request.form.get("password"))
        new_user_id = db.execute("INSERT INTO users (name, username, hash) VALUES(:name, :username, :hash)",
                                 name=request.form.get("name"), username=request.form.get("username"),
                                 hash=hash)

        # unique username constraint violated?
        if not new_user_id:
            return apology("username taken", 400)

        # Remember which user has logged in
        session["user_id"] = new_user_id

        # Display a flash message
        flash("Registered!")

        # Redirect user to home page
        return render_template("homepage.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create Survey"""

    if request.method == "POST":
        button = request.form.get("button")
        if not request.form.get("topic"):
            return apology("must provide topic", 400)
        if  button == "create":
            survey = db.execute("INSERT INTO surveys (topic, creatorid) VALUES(:topic, :creatorid)", topic=request.form.get("topic"), creatorid=session["user_id"])
            return render_template("createq.html",surveyid = survey)
        else:
            """Redirect to HomePage"""
            searches=db.execute("SELECT * FROM surveys ORDER BY views DESC")
            return render_template("homepage.html",searches=searches)
    else:
        return render_template("create.html")


@app.route("/createq", methods=["GET", "POST"])
@login_required
def createq():

    if request.method == "POST":
        button = request.form.get("button")

        if not request.form.get("question"):
            return apology("must provide question", 400)
        elif not request.form.get("op1"):
            return apology("must provide first option", 400)
        elif not request.form.get("op2"):
            return apology("must provide atleast two options", 400)


        if button == "end":
            searches=db.execute("SELECT * FROM surveys ORDER BY views DESC")
            return render_template("homepage.html",searches=searches)


        db.execute("UPDATE users SET count = count + 1 WHERE id=:id",id=session["user_id"])
        question = db.execute("INSERT INTO questions (surveyid, question) VALUES(:surveyid, :question)", surveyid=request.form.get("survId"), question=request.form.get("question"))

        db.execute("INSERT INTO options (option, questionid) VALUES(:option, :questionid)", option=request.form.get("op1"), questionid = question)
        db.execute("INSERT INTO options (option, questionid) VALUES(:option, :questionid)", option=request.form.get("op2"), questionid = question)

        if  button == "addo":
            return render_template("createo.html",questionid=question, surveyid = request.form.get("survId"))
        elif button == "addq":
            """Add Option"""
            return render_template("createq.html",surveyid = request.form.get("survId"))
        elif button == "finish":
            searches=db.execute("SELECT * FROM surveys ORDER BY views DESC")
            return render_template("homepage.html",searches=searches)
    else:
        return render_template("createq.html")

@app.route("/createo", methods=["GET","POST"])
@login_required
def createo():

    if request.method == "POST":
        button = request.form.get("button")

        if not request.form.get("option"):
            return apology("must provide option")

        searches=db.execute("SELECT * FROM surveys ORDER BY views DESC")
        if button == "cancel" :
            return render_template("homepage.html",searches=searches)

        db.execute("INSERT INTO options (option, questionid) VALUES(:option, :questionid)", option=request.form.get("option"), questionid = request.form.get("questionId"))

        if button == "create":
            return render_template("homepage.html",searches=searches)

        if button == "addo":
            return render_template("createo.html",questionid=request.form.get("questionId"), surveyid=request.form.get("survId"))
        else:
            return render_template("createq.html", surveyid=request.form.get("survId"))

    else:
        return render_template("createo.html")
def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)