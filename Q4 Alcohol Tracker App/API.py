import requests
  
# defining the api-endpoint 
API_ENDPOINT = "https://www.thecocktaildb.com/api/json/v1/1/search.php?s=margarita"
URL = "https://www.thecocktaildb.com/api/json/v1/1/random.php"
# your API key here
API_KEY = "1"
  
# data to be sent to api
data = {'api_dev_key':API_KEY}
  
# sending post request and saving response as response object
# r = requests.post(url = API_ENDPOINT, data = data)
r = requests.get(URL)
print(r.json())