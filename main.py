from flask import Flask, render_template, session, g
from flask import request
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.utils import redirect
import os

app = Flask(__name__)
app.secret_key = os.urandom(32)

def get_db():
    client = app.config.get("client")
    if not client:
        client = app.config["client"] = MongoClient()
    user_database = client["user_db"]
    return user_database


@app.route("/", methods=['GET'])
def give_login_page():
    return render_template("login.html")


@app.route("/", methods=["POST"])
def validate_login():
    email = request.form.get("Email")
    password = request.form.get("Password")
    db = get_db()
    user = db.get_collection('User').find_one({"_id": email})
    if user is not None and (user.get('Password') == password):
        session['User'] = user.get('Name')
        session["Email"] = email
        is_admin = user["UserType"] == "Admin"
        db.get_collection('User').update_one({"_id":email}, update={"$set":{"IsActive": True}})
        return render_template("home.html", name=user.get('Name'), is_admin=is_admin)
    else:
        return render_template("login.html", error="Incorrect Email Id or Password")


@app.route("/signup", methods=["GET"])
def get_signup_page():
    return render_template("signup.html")


@app.route("/signup", methods=["POST"])
def save_user():
    args = request.form
    print(args)
    db = get_db()
    try:
        db.get_collection('User').insert_one({"_id": args["Email"], "UserType": "User", **args})
        msg = "User Saved Successfully"
    except DuplicateKeyError:
        msg = "User with this Email already exists"
    return render_template("login.html", error=msg)


@app.route("/database", methods=["GET"])
def get_dbs():
    db = get_db()
    users = list(db.get_collection("User").find({}))
    return str(users)


@app.route('/upload', methods=['POST'])
def upload_file():
    # Get the file from the request
    file = request.files['file']
    pass
    # Check if file is allowed
    # if file and allowed_file(file.filename):
    #     # Generate a random key
    #     key = os.urandom(32)
    #     # Encrypt the file
    #     encrypted_file = encrypt_file(key, file.filename)
    #     # Insert the encrypted file into the database
    #     db = get_db()
    #     db.execute("INSERT INTO files (filename, key) VALUES (?, ?)", [encrypted_file, key])
    #     db.commit()
    #     db.close()
    #     return 'File uploaded successfully'
    # else:
    #     return 'Invalid file type'


@app.route("/home", methods=["GET", "POST"])
def get_home_page():
    if not g.user:
        return render_template("login.html", error="Session Expired")
    else:
        db = get_db()
        user = db.get_collection("User").find_one({"_id":session["Email"]})
        is_admin = user.get("UserType") == "Admin"
        return render_template("home.html", name=g.user, is_admin=is_admin)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("User", None)
    email = session.pop("Email", None)
    db = get_db()
    if email:
        db.get_collection('User').update_one({"_id": email}, update={"$set":{"IsActive": False}})
    return render_template("login.html", error="Logged Out Successfully")


@app.route("/active", methods=["GET", "POST"])
def get_active_users():
    if not g.user:
        return render_template("login.html", error="Session Expired")
    db = get_db()
    users = list(db.get_collection('User').find({"IsActive": True}))
    return render_template("active_users.html", users=users)


@app.route("/send", methods=["GET", "POST"])
def get_users():
    if not g.user:
        return render_template("login.html", error="Session Expired")
    db = get_db()
    users = list(db.get_collection('User').find({},{"_id":1}))
    users = [user["_id"] for user in users]
    return render_template("send.html", users=users)


@app.route("/share", methods=["GET", "POST"])
def share_files():
    if not g.user:
        return render_template("login.html", error="Session Expired")
    args = request.form
    files = args.pop("files")
    emails = list(args.keys())
    return "sucess"


@app.route("/user", methods=["GET", "POST"])
def get_user_management():
    db = get_db()
    users = list(db.get_collection('User').find({}))
    return render_template("users.html", users=users)

@app.before_request
def before_request():
    g.user = None
    if "User" in session:
        g.user = session["User"]


if __name__ == '__main__':
    user_db = get_db()
    collection = user_db["User"]
    if not collection.find_one({"_id": "balu@gmail.com"}):
        admin_user = {"_id": "balu@gmail.com", "Email": "balu@gmail.com", "Purpose": "Education", "Address": "kpm",
                      "UserType": "Admin",
                      "Password": "boobalan@123", "Domain": "Education", "Name": "Boobalan", "Age": 23,
                      "Gender": "Male"}
        collection.insert_one(document=admin_user)
    app.run(debug=True)
