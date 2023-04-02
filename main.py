import os

from bson.objectid import ObjectId
from flask import Flask, render_template, session, g, Response
from flask import request
from gridfs import GridFS
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.routing import BaseConverter
from werkzeug.utils import secure_filename

import encryption_engine


class ObjectIdConverter(BaseConverter):
    def to_python(self, value):
        return ObjectId(value)

    def to_url(self, value):
        return str(value)


app = Flask(__name__)
app.secret_key = os.urandom(32)
app.url_map.converters['ObjectId'] = ObjectIdConverter


def get_db():
    client = app.config.get("client")
    if not client:
        client = app.config["client"] = MongoClient()
    user_database = client["user_db"]
    return user_database


def get_gridfs():
    db = get_db()
    fs = GridFS(db)
    return fs


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
        db.get_collection('User').update_one({"_id": email}, update={"$set": {"IsActive": True}})
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
        user = db.get_collection("User").find_one({"_id": session["Email"]})
        is_admin = user.get("UserType") == "Admin"
        return render_template("home.html", name=g.user, is_admin=is_admin)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("User", None)
    email = session.pop("Email", None)
    db = get_db()
    if email:
        db.get_collection('User').update_one({"_id": email}, update={"$set": {"IsActive": False}})
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
    users = list(db.get_collection('User').find({}, {"_id": 1}))
    users = [user["_id"] for user in users]
    return render_template("send.html", users=users)


@app.route("/share", methods=["POST"])
def share_files():
    if not g.user:
        return render_template("login.html", error="Session Expired")
    users = request.form
    users = list(users.values())
    f = request.files.get("files")
    fs = get_gridfs()
    file_name = secure_filename(f.filename)
    encrypted_file, key = encryption_engine.encrypt_file(f.read())
    oid = fs.put(encrypted_file, filename=file_name)
    db = get_db()
    users = list(db.get_collection('User').find({"_id": {"$in": users}}, {"_id": 1, "files": 1}))
    for user_obj in users:
        user_obj["files"] = user_obj.get("files") or []
        user_obj["files"].append([oid, session["Email"], key])
        db.get_collection("User").update_one({"_id": user_obj["_id"]}, {"$set": {"files": user_obj["files"]}})
    users = list(db.get_collection('User').find({}, {"_id": 1}))
    users = [user["_id"] for user in users]
    return render_template("send.html", users=users)


@app.route("/user", methods=["GET", "POST"])
def get_user_management():
    db = get_db()
    users = list(db.get_collection('User').find({}))
    return render_template("users.html", users=users)


@app.route('/files', methods=["GET", "POST"])
def get_files():
    if not g.user:
        return render_template("login.html", error="Session Expired")
    fs = get_gridfs()
    db = get_db()
    user_obj = db.get_collection("User").find_one({"_id": session["Email"]}, {"files": 1})
    file_list = []
    for file, file_sender_dict, key in user_obj["files"]:
        file_obj = fs.find_one({"_id": file})
        decrypted_file = encryption_engine.decrypt_file(file_obj.read(), key)
        decrypted_file_obj = fs.new_file(filename=file_obj.filename)
        decrypted_file_obj.write(decrypted_file)
        decrypted_file_obj.close()
        file_list.append({
            'filename': decrypted_file_obj.filename,
            'length': decrypted_file_obj.length,
            'upload_date': decrypted_file_obj.upload_date,
            '_id': decrypted_file_obj._id,
            'sender': file_sender_dict
        })
    return render_template('files.html', files=file_list)


@app.route('/download_file/<ObjectId:file_id>')
def download_file(file_id):
    fs = get_gridfs()
    file = fs.get(file_id)
    response = Response(file.read())
    response.headers['Content-Disposition'] = 'attachment; filename=' + file.filename
    response.headers['Content-Type'] = file.content_type
    return response


@app.route('/database/delete')
def delete_database():
    user_db = get_db()
    for collection in user_db.list_collection_names():
        user_db.drop_collection(collection)
    return "Success"


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
        collection.find_one()
    app.run(debug=True, port=5001)
