const LIMIT = 0.15;
const UPDATE_RATE = 5000;

// Add an existing patron to the pool of current patrons
function addExistingPatron(){
    // Obtain value from typeahead search
    search_val = document.getElementById('my_search2').value

    // If search field is empty, click submit and browser will notify user
    if (search_val==""){
        document.getElementById('submit-existing-btn').click();
        return
    }
    id = search_val;
    $.ajax({
        type: "POST",
        url: "/add_existing_patron",
        data: JSON.stringify(id),
        contentType: "application/json",
        dataType: 'json',
        success: function(bool){
            if (bool['success']){
                document.getElementById("submit-existing-btn").click();
            }
            else if (bool['exists']) {
                alert('Patron is already present in bar!');
            }
            else {
                alert('Patron ID does not exist!');
            }
        }
    })
}

// Check if ID is unique when adding new patron
function check_unique(id){
    id = document.getElementById('form_id').value;

    // If field is empty
    if (id==""){
        document.getElementById('submit-new-btn').click();
        return
    }
    // If ID field value is not a number
    else if (isNaN(id)){
        alert('ID must be a number!');
        return
    }
    // If bodyweight field is not a number
    else if (isNaN(document.getElementById('form_bw').value)){
        alert('Bodyweight must be a number!');
        return
    }
    $.ajax({
        type: "POST",
        url: "/check_unique_id",
        data: JSON.stringify(id),
        contentType: "application/json",
        dataType: 'json',
        success: function(bool){
            if (bool['unique']){
                document.getElementById('submit-new-btn').click();
            }
            else {
                alert('Patron ID already exists!')
            }
        }
    })
}

// Remove order and update modal and grid tiles
function removeOrder(orderID){
    $.ajax({
        type: "POST",
        url: "/remove_order",
        data: JSON.stringify(orderID),
        contentType: "application/json",
        dataType: 'json',
        success: function(orders){
            listGen(orders)
            bacDecay()
        }
    })
}

// Used to update selected patron modal and patron's corresponding tile
// Argument is dict of patron's orderID's and corresponding orders, and patron details
function listGen(dict){
    var keys = Object.keys(dict)
    var str = '<ul class="list-group">'
        // Subtract 6 to account for the non-order key-value pairs in dict
        for (let i = keys.length-6; i >=0; i--) {
            str += '<li class="list-group-item">'+ keys[i] +",  " + dict[keys[i]][0] + ',  ' + dict[keys[i]][1].substring(5,26)
                + '<input type="submit"'
                +' class="btn btn-outline-secondary btn-sm pull-right" style="float: right;"'
                +' value="&times;" name="removeOrder" onclick="removeOrder('+keys[i].toString()+')"></li>';
        };
    str += '</ul>';
    // Update list in modal with patron drinks
    document.getElementById("slideContainer").innerHTML = str;

    // Update patron details in modal
    document.getElementById("details").innerHTML = 
                        `<div class="container">
                            <div class="row">
                              <div class="col">Name: `+dict.patronName+`</div>
                              <div class="col">ID: `+dict.patronID.toString()+`</div>
                              <div class="w-100"></div>
                              <div class="col">Sex: `+dict.patronSex+`</div>
                              <div class="col">Bodyweight: `+dict.patronBW.toString()+` kg</div>
                            </div>
                          </div>`;
    
    // Set modal save button function argument with patron id
    document.getElementById("myBtn").setAttribute("onclick", "addOrder("+dict.patronID.toString()+")");
    // Reset typeahead field
    document.getElementById("my_search").value = "";

    // Patron blood alcohol content and update appropriate fields
    patron_bac = parseFloat((dict.bloodAlc*100/LIMIT).toFixed(0)).toString()
    document.getElementById("bloodAlc"+dict.patronID.toString()).innerHTML = patron_bac + ' %'
    document.getElementById("bac").innerHTML = parseFloat(dict.bloodAlc.toFixed(4)).toString(); 
    document.getElementById("bac-capacity").innerHTML = patron_bac;

    // Keep font black if underlimit, else font becomes red
    if (dict.bloodAlc < LIMIT) {
        document.getElementById("bac-data").style = "color:black;";
        document.getElementById("tile-text"+dict.patronID.toString()).style = "color:black;text-align:center;";
        document.getElementById("bloodAlc"+dict.patronID.toString()).style = "color:black;text-align:center;";
    }
    else {
        document.getElementById("bac-data").style = "color:red;";
        document.getElementById("tile-text"+dict.patronID.toString()).style = "color:red;text-align:center;";
        document.getElementById("bloodAlc"+dict.patronID.toString()).style = "color:red;text-align:center;";
    }
    // Automatic resizing of grid tiles for when they get repainted so text fits
    j = 0;
    while( $('#tile'+dict.patronID.toString()+' div').height() > $('#tile'+dict.patronID.toString()).height()+36 && j<10) {
        j++;
        var size = 1.3-j*0.1;
        document.getElementById('tile-text'+dict.patronID.toString()).style.fontSize = (size).toString()+'em';
    }
};

// Retrieves patron details upon clicking on tile to open modal
function openModal(id) {
    $.ajax({
        type: "POST",
        url: "/process_modal",
        data: JSON.stringify(id),
        contentType: "application/json",
        dataType: 'json',
        success: function(orders){
            listGen(orders)
        }
    })
}

// Make Enter key also act as submit button for adding an order in modal
var input = document.getElementById("my_search");
console.log(input);
input.addEventListener("keypress", function(event) {
if (event.key === "Enter") {
    event.preventDefault();
    document.getElementById("myBtn").click();
}
});

// Add a drink order via patron modal
function addOrder(id){
    drink = document.getElementById('my_search').value;
    if (drink == ""){
        alert("Please fill in a drink!")
        return
    }
    $.ajax({
        type: "GET",
        url: "https://www.thecocktaildb.com/api/json/v1/1/search.php?s="+drink,
        dataType: 'json',
        'data': { 'request': "", 'target': 'arrange_url', 'method': 'method_target' },
        success: function(data){
            if (data.drinks !== null && drink.toLowerCase() === data.drinks[0].strDrink.toLowerCase()) {
                data.drinks[0]['patronID'] = id;
                updateOrder(data.drinks[0]);
            }
            else {
                alert("Drink does not exist!");
            }
        }
    })
}

// Repaints only if standard order has been added, else notifies user
function updateOrder(order){
    $.ajax({
        type: "POST",
        url: "/add_order",
        data: JSON.stringify(order),
        contentType: "application/json",
        dataType: 'json',
        success: function(orders){
            if (orders['success']==='non-std'){
                alert('Non-standard drink type or ingredient format.')
            }
            else{
                listGen(orders);
            }                
        }
    })
}

// Repaints tiles with updated blood alcohol content data
function bacDecay(){
    $.ajax({
        type: "GET",
        url: "/alcohol_decay",
        contentType: "application/json",
        dataType: 'json',
        success: function(bac_dict){
            var keys = Object.keys(bac_dict)
            for (let i=0; i<keys.length; i++){
                console.log(bac_dict[keys[i]]*100/LIMIT)
                bac = parseFloat((bac_dict[keys[i]]*100/LIMIT).toFixed(0));
                if (bac < 0){
                    document.getElementById("bloodAlc"+keys[i].toString()).innerHTML = '0 %';
                }
                else{
                    document.getElementById("bloodAlc"+keys[i].toString()).innerHTML = bac.toString() + ' %';
                }
                if (bac < 100){
                    document.getElementById("tile-text"+keys[i].toString()).style = "color:black;text-align:center;";
                    document.getElementById("bloodAlc"+keys[i].toString()).style = "color:black;text-align:center;";
                }
                else{
                    document.getElementById("tile-text"+keys[i].toString()).style = "color:red;text-align:center;";
                    document.getElementById("bloodAlc"+keys[i].toString()).style = "color:red;text-align:center;";
                }
                j = 0;
                while( $('#tile'+keys[i].toString()+' div').height() > $('#tile'+keys[i].toString()).height()+36 && j<10) {
                    j++;
                    var size = 1.3-j*0.1;
                    document.getElementById('tile-text'+keys[i].toString()).style.fontSize = (size).toString()+'em';
                }       
            }
        }
    })
}
// First call when app starts
bacDecay()
// Called at regular rate
setInterval(bacDecay, UPDATE_RATE); 


// Initialise bloodhound typeahead for searching drinks from cocktailsdb.com
var drinks_suggestions = new Bloodhound({
    datumTokenizer: function (datum) {
        return Bloodhound.tokenizers.whitespace(datum.strDrink); // tokenize search string results for bloodhound engine
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace, // tokenize input query
    remote: {
        url: 'https://www.thecocktaildb.com/api/json/v1/1/search.php?s=%QUERY',
        wildcard: '%QUERY',                    // %QUERY will be replaced by users input in
        transform: function(response){
            return response.drinks
        }
    }
});

$('#my_search').typeahead({
    highlight: true,
    minLength: 1
},
{
    name: '',
    source: drinks_suggestions,   // Bloodhound instance is passed as the source
    display: function(item) {        
        return item.strDrink;
    },
    LIMIT: 10,
    templates: {
        // Drop down template
        suggestion: function(item) {
            return '<div>'+ item.strDrink +'</div>';
        },
        // while no result
        pending: function (query) {
            return '<div>No result...</div>';
        }
    }
});

var patrons_suggestions = new Bloodhound({
    datumTokenizer: function (datum) {
        return Bloodhound.tokenizers.whitespace(datum.id); 
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace, 
    remote: {
        url: '/fetch_patrons/%QUERY',               // %QUERY will be replace by users input in
        wildcard: '%QUERY'
    }
});

$('#my_search2').typeahead({
    highlight: true,
    minLength: 1
},
{
    name: '',
    source: patrons_suggestions,   // Bloodhound instance is passed as the source
    display: function(item) {        
        return item.id;
    },
    LIMIT: 10,
    templates: {
        suggestion: function(item) {
            return '<div>'+ item.id + ',  ' + item.name+'</div>';
        },
        pending: function (query) {
            return '<div>No result...</div>';
        }
    }
});
