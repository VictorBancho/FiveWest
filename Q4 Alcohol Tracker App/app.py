from flask import *
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import abort

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'
app.config ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bar2_db'

db = SQLAlchemy(app)

# Database Tables
class Patron(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    age = db.Column(db.Integer)
    bodyweight = db.Column(db.Integer)

class Current(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    bloodAlc = db.Column(db.Float)

class Alcohol(db.Model):
    alcoholType = db.Column(db.String(30), primary_key=True)
    ABV = db.Column(db.Float)

class Order(db.Model):
    orderID = db.Column(db.Integer, primary_key=True)
    patronID = db.Column(db.Integer)
    drinkName = db.Column(db.String(50))

# Association Tables





with app.app_context():
    print('MADE')
    db.create_all()

@app.route("/", methods=['GET','POST'])
def index():
    if request.method=='POST':
        if request.form.get('removeID'):
            id = request.form['id']
            Current.query.filter_by(id=id).delete()
            patrons = Current.query.all()
            db.session.commit()
            return render_template('main.html', patrons = patrons)
        else:
            name = request.form['patron_name']
            id = request.form['patron_id']
            age = request.form['patron_age']
            bw = request.form['patron_bodyweight']

            if not name or not id or not age or not bw:
                flash('Please fill all fields!')
            else:
                db.session.add(Patron(id = id, name=name, age = age, bodyweight = bw))
                db.session.add(Current(id = id, name = name, bloodAlc = 0))
                patrons = Current.query.all()
                db.session.commit()
                return render_template('main.html', patrons = patrons)

    patrons = Current.query.all()
    return render_template('main.html', patrons=patrons)





    
if __name__ == "__main__":
    app.run(debug=True)
