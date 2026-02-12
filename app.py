import os

from flask import Flask, render_template

#Configure application
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("layout.html")
