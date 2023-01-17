from flask import *
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime as dt, timedelta as tdel
import requests
import webbrowser
from threading import Timer

# Initialise Flask API instance and connect it to database
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret key'
app.config ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bar.db' 

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
    dateTime = db.Column(db.DateTime, default=dt.now()) #typo

with app.app_context():
    # Creates database if does not exist
    db.create_all()
    # Adds common ingredients 
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

# Global variables
RATE = 0.015        # Average rate human metabolises alcohol (%)
FACTOR = 1          # For test purposes, speeds up alcohol metabolism

# Main page View Function
@app.route("/", methods=['GET','POST'])
def index():
    if request.method =='POST':
        # If a patron 'tile' is clicked on, posts patron details for modal
        if request.form.get('modalID'):
            id = request.form['id']
            patronView = [Current.query.all()[id]]
            return render_template('main.html', patronView = patronView)
        
        # If patron tiles is removed, updates and repaints
        elif request.form.get('removeID'):
            id = request.form['id']
            Current.query.filter_by(id=id).delete()
            patrons = Current.query.all()
            db.session.commit()
            return render_template('main.html', patrons = patrons)

        # If existing patron is added to Current table, javascript code callse on
        # the python addExistingPatron() function to update current, the html
        # form then posts. Reason: the browser notifies users to fill empty required fields
        # when form submit button is pressed. Submitting via javascript loses this feature.
        elif request.form.get('search'):
            return redirect('/')
        
        # Add a new patron to Patron and Current table
        else:
            timeIn = dt.now()
            name = request.form['patron_name']
            id = request.form['patron_id']
            sex = request.form['patron_sex']
            bw = request.form['patron_bodyweight']
            
            db.session.add(Patron(id = id, name=name, sex = sex, bodyweight = bw))
            db.session.add(Current(timeIn=timeIn, id = id, name = name, bloodAlc = 0))
            db.session.commit()

            # Return combined object with required data
            patrons = patrons = db.session.query(Current.timeIn, Current.bloodAlc, Patron.name, Patron.id, 
                        Patron.sex, Patron.bodyweight).join(Patron, isouter=True).all()
            return render_template('main.html', patrons = patrons)
    
    # Else page is simply repainted (SSR)
    patrons = db.session.query(Current.timeIn, Current.bloodAlc, Patron.name, Patron.id, 
                            Patron.sex, Patron.bodyweight).join(Patron, isouter=True).all()
    return render_template('main.html', patrons=patrons)

# When modal is opened, repaints designated fields with updated specifics
@app.route('/process_modal', endpoint = 'func1', methods=['POST', 'GET'])
def viewModal():
    if request.method == "POST":
        id = request.get_json()
        selected_patron = Patron.query.filter(Patron.id==id).first()
        current_patron = Current.query.filter(Current.id==id).first()
        bac = 0
        # Update the patron bac by how much it would have decayed.
        if (current_patron.bloodAlc > 0):
            try:
                now = dt.now()
                time_delta = now-Order.query.filter(Order.patronID==id).order_by(Order.orderID.desc()).first().dateTime
                bac = current_patron.bloodAlc - RATE*time_delta.total_seconds()/3600*FACTOR    
                if bac < 0: bac = 0
            except:
                print('Error: Blood alcohol with no order')
        else: bac = 0
        print("printing after "+str(bac))
        # Return all of patron's orders, and the patron details in dict
        orderDict = dict()
        orders = Order.query.filter(Order.patronID==id).all()
        for order in orders:
            orderDict[f'{order.orderID}'] = [order.drinkName, order.dateTime]
        orderDict['patronID'] = selected_patron.id
        orderDict['patronSex'] = selected_patron.sex
        orderDict['patronName'] = selected_patron.name
        orderDict['patronBW'] = selected_patron.bodyweight
        orderDict['bloodAlc'] = bac
    return jsonify(orderDict)

# Called when a patron order is added through the modal
@app.route('/add_order', endpoint = 'func2', methods=['POST', 'GET'])
def addOrder():
    if request.method == "POST":
        drink_data = request.get_json()

        # Find ml of alc in drink
        orderAlc = drinkAlc(drink_data)

        # For non-standard drinks
        if orderAlc < 0:
            return jsonify({'success':'non-std'})

        # Select patron rows from Patron and Current tables
        patronID = drink_data['patronID']
        patronData = Patron.query.filter(Patron.id==patronID).first()
        currentPatron = Current.query.filter(Current.id==patronID).first()
        orderDateTime = dt.now()

        # Add patron order to Order table
        db.session.add(Order(patronID = patronID, drinkName = drink_data['strDrink'], dateTime = orderDateTime))

        # Try update blood alcohol if patron has had a previous drink
        try:
            lastOrder = Order.query.filter(Order.patronID==patronID).order_by(Order.orderID.desc()).first().dateTime
            time_delta = (orderDateTime - lastOrder).total_seconds()
            orderDecay = RATE*time_delta/3600*FACTOR
            # If the BAC decay is greater than current BAC, only this order contributes to patron's BAC
            if currentPatron.bloodAlc - orderDecay <= 0: currentPatron.bloodAlc = alcSat(orderAlc, patronData.bodyweight, patronData.sex)
            else: currentPatron.bloodAlc += alcSat(orderAlc, patronData.bodyweight, patronData.sex) - orderDecay
        except:
            currentPatron.bloodAlc = alcSat(orderAlc, patronData.bodyweight, patronData.sex) # first order
        db.session.commit()

        # Create dictionary of patron orders and details and return
        orders = Order.query.filter(Order.patronID==patronID).all()
        orderDict = dict()
        for order in orders:
            orderDict[f'{order.orderID}'] = [order.drinkName, order.dateTime]
        orderDict['patronID'] = patronData.id
        orderDict['patronSex'] = patronData.sex
        orderDict['patronName'] = patronData.name
        orderDict['patronBW'] = patronData.bodyweight
        orderDict['bloodAlc'] = currentPatron.bloodAlc
    return jsonify(orderDict)

# When user selects to remove patron order from modal
@app.route('/remove_order', endpoint = 'func3', methods=['POST', 'GET'])
def removeOrder():
    if request.method == "POST":
        orderID = request.get_json()

        # Find order from Order table using posted ID and use to get patron details
        selected_order = Order.query.filter(Order.orderID==orderID).first()
        patronID = selected_order.patronID
        selected_patron = Patron.query.filter(Patron.id==patronID).first()

        # Update patron BAC to account for deleted order
        drinkDict = getDrinkDict(selected_order.drinkName)
        orderAlc = drinkAlc(drinkDict)
        orderBAC = alcSat(orderAlc, selected_patron.bodyweight, selected_patron.sex)
        time_delta = (dt.now() - selected_order.dateTime).total_seconds()
        alcDecay = RATE*time_delta/3600*FACTOR
        selected_currentpatron = Current.query.filter(Current.id==patronID).first()
        del_bac = (orderBAC - alcDecay)

        # If still postive BAC effect from deleted drink, subtract amount, ensuring patron BAC is non-negative.
        if del_bac > 0: selected_currentpatron.bloodAlc -= del_bac
        if (selected_currentpatron.bloodAlc < 0): selected_currentpatron.bloodAlc = 0

        # Execute delete on table
        Order.query.filter(Order.orderID==orderID).delete()
        db.session.commit()

        # Create dict for return
        orders = Order.query.filter(Order.patronID==patronID).all()
        orderDict = dict()
        for order in orders:
            orderDict[f'{order.orderID}'] = [order.drinkName, order.dateTime]
        orderDict['patronID'] = selected_patron.id
        orderDict['patronSex'] = selected_patron.sex
        orderDict['patronName'] = selected_patron.name
        orderDict['patronBW'] = selected_patron.bodyweight
        orderDict['bloodAlc'] = selected_currentpatron.bloodAlc
        print('deleted')
    return jsonify(orderDict)

# Called regularly by javascript async function, updates grid of patron tiles.
@app.route('/alcohol_decay', endpoint = 'func4', methods=['POST','GET'])
def decay():
    # Create dict object to be filled with current patron BAC data.
    bac_dict = {}
    current_table = Current.query.all()
    now = dt.now()

    # Iterate through all current patrons
    for patron in current_table:
        print(patron.bloodAlc)
        # If there is alcohol to be metabolised
        try:
            latest_order_time = Order.query.filter(Order.patronID==patron.id).order_by(Order.orderID.desc()).first().dateTime
            time_delta = now-latest_order_time
            bac_dict[patron.id] = patron.bloodAlc - RATE*time_delta.total_seconds()/3600*FACTOR
        # Otherwise BAC is zero
        except:
            patron.bloodAlc = 0
            db.session.commit()
            bac_dict[patron.id] = 0

        # Ensure no negative BAC, set to zero
        if bac_dict[patron.id] < 0: 
            bac_dict[patron.id] = 0     # no negative bac
            patron.bloodAlc = 0         # reset patron bac
            db.session.commit()
    return jsonify(bac_dict)

# When adding new patron, checks that ID is not already taken
@app.route('/check_unique_id', endpoint = 'func5', methods=['POST','GET'])
def checkID():
    id = request.get_json()
    unique = True
    count = Patron.query.filter_by(id=id).count()
    if count > 0: unique = False
    return jsonify({'unique':unique})

# Called by the typeahead in the modal from 'Add Existing Patron'button, to make search easier.
@app.route('/fetch_patrons/<id>', endpoint = 'func6', methods=['POST','GET'])
def fetchPatrons(id):
    query_length = len(id)

    # Only be able to search for patrons that are not current
    patrons = db.session.query(Patron.id, Patron.name, Patron.sex, 
                Patron.bodyweight).filter(~Patron.id.in_(db.session.query(Current.id))).all()

    # Create array to be filled with dict object (sent as JSON array for typeahead)
    patronArr = []
    i = 0
    for patron in (patrons):
        # Since user types id digits from left to right, turn patron id to string and compare first n digits
        if str(patron.id)[:query_length] == id:
            # if a match, append with patron details
            patronArr.append({})
            patronArr[i]['id'] = patron.id
            patronArr[i]['name'] = patron.name
            patronArr[i]['sex'] = patron.sex
            patronArr[i]['bodyweight'] = patron.bodyweight
            i += 1
    return jsonify(patronArr)
        
# Called when a user decides to add an existing patron, after having selected
@app.route('/add_existing_patron', endpoint = 'func7', methods=['POST','GET'])
def addExistingPatron():
    id = request.get_json()
    bac = 0

    # this accounts for if patron already exists in current patrons
    count = Current.query.filter(Current.id == id).count()
    if count > 0:
        return jsonify({'success':False, 'exists':True})
    
    # Get all orders of the patron from within 24 hours and calculate their net effect
    # on patron's BAC. We are bringing back a patron that left the bar earlier.
    try:
        patron_orders = Order.query.filter(Order.patronID==id and Order.dateTime > dt.now() - tdel(days=1)).all()
        patron = Patron.query.filter(Patron.id==id).first()
        for order in patron_orders:
            alc = getDrinkAlc(order.drinkName)
            drink_bac = alcSat(alc, patron.bodyweight, patron.sex)
            time_delta = dt.now()-order.dateTime
            bac += drink_bac - RATE*time_delta.total_seconds()/3600*FACTOR       # reduce
        db.session.add(Current(timeIn = dt.now(), name = Patron.query.filter(Patron.id==id).first().name, 
                                        id = id, bloodAlc = bac))
        db.session.commit()
        return jsonify({'success':True})
    # Except if no such patron ID exists
    except:
        return jsonify({'success':False, 'exists':False})

# Button at bottom of page: Resets patron related data tables
@app.route('/reset', endpoint = 'func8', methods=['POST','GET'])
def reset():
    db.session.query(Patron).delete()
    db.session.query(Current).delete()
    db.session.query(Order).delete()
    db.session.commit()
    return redirect('/')

# Return blood alcohol content using time independent Widmark formula
def alcSat(alc, bw, sex):
    ratio = 0.68 if sex[0] == 'M' else 0.55
    bac = alc*0.79/(ratio*bw*10)    # *100% /1000g
    return round(bac,5)

# Get drink details dict from cocktaildb.com
def getDrinkDict(drinkName):
    URL = "https://www.thecocktaildb.com/api/json/v1/1/search.php?s=" + drinkName
    return requests.get(URL).json()['drinks'][0]

# get drink alcohol content from Drink table
def getDrinkAlc(drinkName):
    return Drink.query.filter(Drink.name==drinkName).first().alc_content

# For given drink dict, determine drink alcohol content
def drinkAlc(drinkDict):            
    drinkName = drinkDict['strDrink']
    # Try access directly from drink table
    try:
        return getDrinkAlc(drinkName)
    # If not in table, use ingredients
    except:
        URL = 'https://www.thecocktaildb.com/api/json/v1/1/search.php?i='
        alc = 0
        # Iterate through ingredients
        for i in range(1,16):
            ingredient = drinkDict[f'strIngredient{i}']
            if ingredient == None:
                break       # Reached last ingredient
            else:
                # Try to determine ingredient alcohol content algorithmically
                # Requires ingredient type to have non-None value for alcohol content 
                # in cocktaildb.
                try:
                    # First look up in local Ingredient table
                    try:
                        ingredientABV = Ingredient.query.filter(Ingredient.name==ingredient).first().ABV
                        if ingredientABV == 0:      # No alcohol content
                            continue
                    # Not in table - look up using DB API
                    except:
                        ingredientDict = requests.get(URL+ingredient).json()['ingredients'][0]
                        ingredientABV = ingredientDict['strABV']

                        if ingredientABV == None and ingredientDict['strAlcohol']=='Yes': 
                            alc = -1        # implies bad formatting, drink is not added and user is notified
                            break
                        elif ingredientABV == None:
                            db.session.add(Ingredient(name = ingredient, ABV = 0))  # Update table
                            db.session.commit()
                            continue        # No alcohol content

                        ingredientABV = float(ingredientABV)
                        db.session.add(Ingredient(name = ingredient, ABV = ingredientABV))
                        db.session.commit()
                    
                    # Convert measure amount to ml.
                    amount = convertAmount(drinkDict[f'strMeasure{i}'])
                    alc += amount*ingredientABV/100
                # Except if non-standard measure
                except: 
                    print('Non-standard drink type or ingredient format.')
                    alc = -1
        # Add drink to Table for quick alcohol_content lookup
        db.session.add(Drink(name= drinkName, alc_content = alc))
        db.session.commit()
        return alc

# Takes ingredient 'measure' string and converts to ml
def convertAmount(strAmnt):
    arr = strAmnt.split()
    scale = 1 
    measure = 0

    # Convert unites to equivalent ml 
    if arr[-1].lower() == 'oz':     # fluid ounces
        scale = 30
    elif arr[-1].lower() == 'cl':  
        scale = 10
    elif arr[-1].lower() == 'dl':
        scale = 100
    elif arr[-1].lower() == 'shot': # south african standard 25 ml
        scale = 25
    elif arr[-1].lower() == 'ml':
        scale = 1
    else: return None               # Non-standard

    # For specific measure values e.g: 2-3 oz, 1 1/2 oz, 4.5 cL.
    if '-' in arr[-2]:
        measure = int(arr[-2].split('-')[-1])
    elif '/' in arr[-2]:
        measure = int(arr[-2][0])/int(arr[-2][-1])
        if len(arr) == 3:
            measure += int(arr[0])  # 1 1/2 format
    else:
        measure = float(arr[0])   #standard decimal
    return measure * scale

# Launch open webapp upon Flask initialising - does not work through Docker
def open_browser():
      webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(debug=False)
