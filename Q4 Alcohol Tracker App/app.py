from flask import *
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import abort
from datetime import datetime as dt
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'
app.config ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bar8_db'

db = SQLAlchemy(app)

# Database Tables
class Patron(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    sex = db.Column(db.String(10))
    bodyweight = db.Column(db.Integer)

class Current(db.Model):
    timeIn = db.Column(db.String(30), primary_key=True)
    name = db.Column(db.String(50))
    bloodAlc = db.Column(db.Float)  #net blood alc, without decay
    id = db.Column(db.Integer, db.ForeignKey('patron.id'), nullable=False)
    patron = db.relationship(Patron, backref=db.backref('patron', lazy=True))

class Ingredient(db.Model): ### CHANGE TO INGREDIENTS
    name = db.Column(db.String(30), primary_key=True)
    ABV = db.Column(db.Float)

class Drink(db.Model):
    name = db.Column(db.String(30), primary_key=True)
    alc_content = db.Column(db.Float)

class Order(db.Model):
    orderID = db.Column(db.Integer, primary_key=True)
    patronID = db.Column(db.Integer)
    drinkName = db.Column(db.String(50))
    dataTime = db.Column(db.DateTime, default=dt.now()) #typo

with app.app_context():
    db.create_all()
    try:
        db.session.add(Ingredient(name='Vodka', ABV=40))
        db.session.add(Ingredient(name='Tequila', ABV=40))
        db.session.add(Ingredient(name='Gin', ABV=40))
        db.session.add(Ingredient(name='Rum', ABV=40))
        db.session.add(Ingredient(name='Scotch', ABV=40))
        db.session.add(Ingredient(name='Triple sec', ABV=40))
        db.session.add(Ingredient(name='Light rum', ABV=40))
        db.session.commit()
    except:
        print('db initialised')




# Association Tables
metabolic_rate = 0.015
accelerator = 1

@app.route("/", methods=['GET','POST'])
def index():
    if request.method =='POST':
        print('POST_______XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
        if request.form.get('modalID'):
            print('MODAL_______XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
            id = request.form['id']
            patronView = [Current.query.all()[id]]
            return render_template('main.html', patronView = patronView)
        elif request.form.get('removeID'):
            print("REMOVE_____XXXXXXXXXXXXXXXXXXXXXxx")
            id = request.form['id']
            Current.query.filter_by(id=id).delete()
            patrons = Current.query.all()
            db.session.commit()
            return render_template('main.html', patrons = patrons)
        elif request.form.get('search'):
            return redirect('/')
        else:
            print("ADD_______XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            timeIn = dt.now()
            name = request.form['patron_name']
            id = request.form['patron_id']
            sex = request.form['patron_sex']
            bw = request.form['patron_bodyweight']
            
            db.session.add(Patron(id = id, name=name, sex = sex, bodyweight = bw))
            db.session.add(Current(timeIn=timeIn, id = id, name = name, bloodAlc = 0))
            db.session.commit()
            patrons = patrons = db.session.query(Current.timeIn, Current.bloodAlc, Patron.name, Patron.id, 
                        Patron.sex, Patron.bodyweight).join(Patron, isouter=True).all()
            return render_template('main.html', patrons = patrons)
    print('PAGE_______XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
    patrons = db.session.query(Current.timeIn, Current.bloodAlc, Patron.name, Patron.id, 
                            Patron.sex, Patron.bodyweight).join(Patron, isouter=True).all()
    print(Patron.query.all())
    return render_template('main.html', patrons=patrons)

@app.route('/process_modal', endpoint = 'func1', methods=['POST', 'GET'])
def viewModal():
    print("VIEWING_MODAL________XXXXXXXXXXXXXXXXXXXXXXXXXXxx")
    if request.method == "POST":
        id = request.get_json()
        selected_patron = Patron.query.filter(Patron.id==id).first()
        current_patron = Current.query.filter(Current.id==id).first()
        if (current_patron.bloodAlc > 0):
            try:
                now = dt.now()
                time_delta = now-Order.query.filter(Order.patronID==id).order_by(Order.orderID.desc()).first().dataTime
                bac = current_patron.bloodAlc - 0.015*time_delta.total_seconds()/3600*50        # reduce
                if bac < 0: bac = 0
            except:
                print('Error: Blood alcohol with no order')
        else: bac = 0
        orderDict = dict()
        orders = Order.query.filter(Order.patronID==id).all()
        for order in orders:
            orderDict[f'{order.orderID}'] = order.drinkName
        orderDict['patronID'] = selected_patron.id
        orderDict['patronSex'] = selected_patron.sex
        orderDict['patronName'] = selected_patron.name
        orderDict['patronBW'] = selected_patron.bodyweight
        orderDict['bloodAlc'] = bac
    return jsonify(orderDict)

@app.route('/add_order', endpoint = 'func2', methods=['POST', 'GET'])
def addOrder():
    print("ADD_ORDER________XXXXXXXXXXXXXXXXXXXXXXXXXXxx")
    if request.method == "POST":
        drink_data = request.get_json()
        orderABV = drinkABV(drink_data)
        print(orderABV)
        if orderABV < 0:
            return jsonify({'success':'non-std'})
        print(orderABV)
        patronID = drink_data['patronID']
        patronData = Patron.query.filter(Patron.id==patronID).first()
        currentPatron = Current.query.filter(Current.id==patronID).first()
        orderDateTime = dt.now()
        db.session.add(Order(patronID = patronID, drinkName = drink_data['strDrink'], dataTime = orderDateTime))
        try:
            lastOrder = Order.query.filter(Order.patronID==patronID).order_by(Order.orderID.desc()).first().dataTime
            time_delta = (orderDateTime - lastOrder).total_seconds()
            print('order added')
            orderDecay = 0.015*time_delta/3600*50
            ### ADD ALC SAT FUNC
            if currentPatron.bloodAlc - orderDecay <= 0: currentPatron.bloodAlc = alcSat(orderABV, patronData.bodyweight, patronData.sex)
            else: currentPatron.bloodAlc += alcSat(orderABV, patronData.bodyweight, patronData.sex) - orderDecay
        except:
            currentPatron.bloodAlc = alcSat(orderABV, patronData.bodyweight, patronData.sex) # first order
        db.session.commit()
        print('committed bloodalc from order and added order')
        orders = Order.query.filter(Order.patronID==patronID).all()
        orderDict = dict()
        for order in orders:
            orderDict[f'{order.orderID}'] = order.drinkName
        orderDict['patronID'] = patronData.id
        orderDict['patronSex'] = patronData.sex
        orderDict['patronName'] = patronData.name
        orderDict['patronBW'] = patronData.bodyweight
        orderDict['bloodAlc'] = currentPatron.bloodAlc
    return jsonify(orderDict)

def alcSat(alc, bw, sex):
    ratio = 0.68 if sex[0] == 'M' else 0.55
    bac = alc*0.79/(ratio*bw*10)    # *100% /1000g
    return round(bac,5)

def getDrinkDict(drinkName):
    URL = "https://www.thecocktaildb.com/api/json/v1/1/search.php?s=" + drinkName
    return requests.get(URL).json()['drinks'][0]

def getDrinkABV(drinkName):
    return Drink.query.filter(Drink.name==drinkName).first().alc_content

def drinkABV(drinkDict):            # function naming? ABV?
    drinkName = drinkDict['strDrink']
    try:
        return getDrinkABV(drinkName)
    except:
        URL = 'https://www.thecocktaildb.com/api/json/v1/1/search.php?i='
        alc = 0
        for i in range(1,16):
            ingredient = drinkDict[f'strIngredient{i}']
            print(ingredient)
            if ingredient == None:
                break
            else:
                ### Store each ingredient in db with first use, check db first.
                try:
                    try:
                        ting = Ingredient.query.filter(Ingredient.name=='Triple sec').first()
                        print(ting)
                        ingredientABV = Ingredient.query.filter(Ingredient.name==ingredient).first().ABV
                        if ingredientABV == 0:
                            continue
                    except:
                        ingredientDict = requests.get(URL+ingredient).json()['ingredients'][0]
                        ingredientABV = ingredientDict['strABV']
                        if ingredientABV == None and ingredientDict['strAlcohol']=='Yes': 
                            alc = -1
                            break
                        elif ingredientABV == None:
                            db.session.add(Ingredient(name = ingredient, ABV = 0))
                            db.session.commit()
                            continue
                        ingredientABV = float(ingredientABV)
                        db.session.add(Ingredient(name = ingredient, ABV = ingredientABV))
                        db.session.commit()
                    # print('first_____________'+drinkDict[f'strMeasure{i}']+' '+ingredient)
                    amount = convertAmount(drinkDict[f'strMeasure{i}'])
                    # print('second____________'+str(amount))
                    
                    print((ingredientABV))
                    print(amount)
                    alc += amount*ingredientABV/100
                    print('done')
                    # print('fourth___________'+str(alc))
                except: 
                    print('Non-standard drink type or ingredient format.')
                    print(drinkDict[f'strMeasure{i}'])
                    print(ingredient)
                    alc = -1
        db.session.add(Drink(name= drinkName, alc_content = alc))
        db.session.commit()
        return alc




def convertAmount(strAmnt):
    arr = strAmnt.split()
    scale = 1 
    measure = 0
    if arr[-1].lower() == 'oz':
        scale = 30
    elif arr[-1].lower() == 'cl': # for ml scale = 1
        scale = 10
    elif arr[-1].lower() == 'dl':
        scale = 100
    elif arr[-1].lower() == 'shot':
        scale = 25
    elif arr[-1].lower() == 'cup':  # remove
        scale = 250
    elif arr[-1].lower() == 'ml':
        scale = 1
    else: return None
    if '-' in arr[-2]:
        measure = int(arr[-2].split('-')[-1])
    elif '/' in arr[-2]:
        measure = int(arr[-2][0])/int(arr[-2][-1])
        if len(arr) == 3:
            measure += int(arr[0])  # 1 1/2 format
    else:
        measure = float(arr[0])   #standard decimal
    return measure * scale



@app.route('/remove_order', endpoint = 'func3', methods=['POST', 'GET'])
def removeOrder():
    print("DEL_ORDER________XXXXXXXXXXXXXXXXXXXXXXXXXXxx")
    if request.method == "POST":
        orderID = request.get_json()
        selected_order = Order.query.filter(Order.orderID==orderID).first()
        patronID = selected_order.patronID
        selected_patron = Patron.query.filter(Patron.id==patronID).first()
        drinkDict = getDrinkDict(selected_order.drinkName)
        orderABV = drinkABV(drinkDict)
        orderAlc = alcSat(orderABV, selected_patron.bodyweight, selected_patron.sex)
        time_delta = (dt.now() - selected_order.dataTime).total_seconds()
        # Order.query.filter(Order.patronID==selected_patron.id).order_by(Order.orderID.desc()).first().dataTime).total_seconds()
        alcDecay = 0.015*time_delta/3600*50      # reduce
        selected_currentpatron = Current.query.filter(Current.id==patronID).first()
        del_bac = (orderAlc - alcDecay)
        if del_bac > 0: selected_currentpatron.bloodAlc -= del_bac
        if (selected_currentpatron.bloodAlc < 0): selected_currentpatron.bloodAlc = 0
        Order.query.filter(Order.orderID==orderID).delete()
        db.session.commit()
        orders = Order.query.filter(Order.patronID==patronID).all()
        orderDict = dict()
        for order in orders:
            orderDict[f'{order.orderID}'] = order.drinkName
        orderDict['patronID'] = selected_patron.id
        orderDict['patronSex'] = selected_patron.sex
        orderDict['patronName'] = selected_patron.name
        orderDict['patronBW'] = selected_patron.bodyweight
        orderDict['bloodAlc'] = selected_currentpatron.bloodAlc
        print('deleted')
    return jsonify(orderDict)

@app.route('/alcohol_decay', endpoint = 'func4', methods=['GET'])
def decay():
    print("DECAY________XXXXXXXXXXXXXXXXXXXXXXXXXXxx")
    bac_dict = {}
    current_table = Current.query.filter(Current.bloodAlc>0).all()
    print('queried for decay')
    now = dt.now()
    for patron in current_table:
        # if patron.bloodAlc > 0: ## IMPLEMENT
        print(patron.name)
        print(patron.bloodAlc)
        try:
            print('START OF TRY')
            orders = Order.query.filter(Order.patronID==patron.id).all()
            print(orders)
            # for order in orders:
            #     print(order.dataTime)
            latest_order_time = Order.query.filter(Order.patronID==patron.id).order_by(Order.orderID.desc()).first().dataTime
            print(latest_order_time)
            time_delta = now-latest_order_time
            print(time_delta)
            bac_dict[patron.id] = patron.bloodAlc - 0.015*time_delta.total_seconds()/3600*50        # reduce
            print('END OF TRY')
        except:
            print('EXECUTE EXCEPT')
            patron.bloodAlc = 0
            db.session.commit()
            bac_dict[patron.id] = 0
        print(bac_dict[patron.id])
        # else: bac_dict[patron.id] = 0
        if bac_dict[patron.id] < 0: 
            print('SETTING TO ZERO______XXXXXXXXXXXXXXXXXXXXXxxxx')
            print(bac_dict[patron.id])
            bac_dict[patron.id] = 0     # no negative bac
            patron.bloodAlc = 0         # reset patron bac
            db.session.commit()
        print(bac_dict[patron.id])
    return jsonify(bac_dict)

@app.route('/check_unique_id', endpoint = 'func5', methods=['POST','GET'])
def checkID():
    id = request.get_json()
    unique = True
    count = Patron.query.filter_by(id=id).count()
    if count > 0: unique = False
    return jsonify({'unique':unique})

@app.route('/fetch_patrons/<id>', endpoint = 'func6', methods=['POST','GET'])
def fetchPatrons(id):
    print('fetch')
    query_length = len(id)
    # patrons = Patron.query.filter(~Patron.id.in_(Current.query.all())).all()
    patrons = db.session.query(Patron.id, Patron.name, Patron.sex, Patron.bodyweight).filter(~Patron.id.in_(db.session.query(Current.id))).all()
    print(patrons)
    patronArr = []
    i = 0
    for patron in (patrons):
        print(id)
        print(str(patron.id)[:query_length])
        if str(patron.id)[:query_length] == id:
            patronArr.append({})
            patronArr[i]['id'] = patron.id
            patronArr[i]['name'] = patron.name
            patronArr[i]['sex'] = patron.sex
            patronArr[i]['bodyweight'] = patron.bodyweight
            i += 1
    return jsonify(patronArr)
        
@app.route('/add_existing_patron', endpoint = 'func7', methods=['POST','GET'])
def addExistingPatron():
    print('ADD_EXISTING__XXXXXXXXXX')
    id = request.get_json()
    bac = 0
    count = Current.query.filter(Current.id == id).count()
    if count > 0:
        return jsonify({'success':False, 'exists':True})
    try:
        patron_orders = Order.query.filter(Order.patronID==id).all()
        patron = Patron.query.filter(Patron.id==id).first()
        for order in patron_orders:
            alc = getDrinkABV(order.drinkName)
            drink_bac = alcSat(alc, patron.bodyweight, patron.sex)
            time_delta = dt.now()-order.dataTime
            bac += drink_bac - 0.015*time_delta.total_seconds()/3600*50        # reduce
        db.session.add(Current(timeIn = dt.now(), name = Patron.query.filter(Patron.id==id).first().name, 
                                        id = id, bloodAlc = bac))
        db.session.commit()
        print('added')
        return jsonify({'success':True})
    except:
        print('failed')
        return jsonify({'success':False, 'exists':False})

@app.route('/reset', endpoint = 'func8', methods=['POST','GET'])
def reset():
    db.session.query(Patron).delete()
    db.session.query(Current).delete()
    db.session.query(Order).delete()
    db.session.commit()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
