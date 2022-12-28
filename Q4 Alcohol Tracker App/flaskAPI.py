from flask import *

app = Flask(__name__)

@app.route("/")
def start():
    return render_template("front.html")

# @app.route("./templates/font.html", methods=["POST"])
# def update():

    
if __name__ == "__main__":
    app.run(debug=True)
