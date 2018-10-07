from flask import Flask, render_template, request, url_for, redirect
# from requests_toolbelt.adapters import appengine
from clarifai.rest import ClarifaiApp
from clarifai.rest import Image as CImage
import json
import httplib2
import re

# clarifai_key = os.environ['CLARIFAI_API_KEY']
clar_app = ClarifaiApp()

app = Flask(__name__)
app.config.update(
	SECRET_KEY='bf3934t97wgbyisdfbwegioew4fbef4gt5',
	SECURITY_PASSWORD_SALT='super-salt-salty-salt-salt-nacl'
)
# appengine.monkeypatch()

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/confirm')
def confirm():
	items = request.args['items']
	app.logger.info(request.get_json())
	app.logger.info(items)
	return render_template('confirm.html', items = json.loads(items))
	
@app.route('/api/request', methods=['POST'])
def image_request():
	name = request.headers.get('name')
	image = request.get_json(force=True).split(';')[-1].split(',')[-1]
	name_split = name.split('.')
	file_name = name_split[0]
	extension = name_split[1]
	url = 'https://www.googleapis.com/upload/storage/v1/b/recipeanut-images/o?uploadType=media&name={}'.format(file_name)
	body = image.decode('base64')
	headers={
		"Content-Type": "image/{}".format(extension)
	}
	http = httplib2.Http()
	resp_headers, resp_body = http.request(url, method='POST', headers=headers, body=body)
	
	serving_url = 'https://storage.googleapis.com/recipeanut-images/{}'.format(file_name)
	
	model = clar_app.models.get('food-items-v1.0')
	image = CImage(url=serving_url)
	resp = model.predict([image])
	if resp['status']['description'] == 'Ok':
		items = {}
		index = 0
		for item in resp['outputs'][0]['data']['concepts']:
			food = extract_image_data(item)
			if food != '':
				items[index] = food
				index += 1
		return json.dumps(items)
	return 'Image could not be read.'
	
@app.route('/api/mobile/request')
def mobile_request():
	name = request.headers.get('name')
	image = request.get_data()
	name_split = name.split('.')
	file_name = name_split[0]
	extension = name_split[1]
	url = 'https://www.googleapis.com/upload/storage/v1/b/recipeanut-images/o?uploadType=media&name={}'.format(file_name)
	body = image
	headers={
		"Content-Type": "image/{}".format(extension)
	}
	http = httplib2.Http()
	resp_headers, resp_body = http.request(url, method='POST', headers=headers, body=body)
	app.logger.info(resp_body)
	
	serving_url = 'https://storage.googleapis.com/recipeanut-images/{}'.format(file_name)
	
	model = clar_app.models.get('food-items-v1.0')
	image = CImage(url=serving_url)
	resp = model.predict([image])
	
	if resp['status']['description'] == 'Ok':
		items = []
		for item in resp['outputs'][0]['data']['concepts']:
			food = extract_image_data(item)
			if food != '':
				items.append(food)
		return items
	return 'Image could not be read.'
	

@app.route('/api/search', methods=['POST'])
def search():
	http = httplib2.Http()
	app.logger.info(request.get_json(force=True))
	ingredients = json.loads(request.data)
	ing_query = serialize_ingredients(ingredients)
	url = 'http://www.recipepuppy.com/api/?i={}'.format(ing_query)
	resp_headers, resp_body = http.request(url, method='GET')
	results = json.loads(resp_body)
	recipes = parse_recipes(results)
	return json.dumps(recipes)
	
@app.route('/api/mobile/search', methods=['POST'])
def mobile_search():
	http = httplib2.Http()
	app.logger.info(request.get_json(force=True))
	ingredients = json.loads(request.data)
	ing_query = serialize_ingredients(ingredients)
	url = 'http://www.recipepuppy.com/api/?i={}'.format(ing_query)
	resp_headers, resp_body = http.request(url, method='GET')
	results = json.loads(resp_body)
	recipes = parse_recipes(results)
	return json.dumps(recipes)
	
	
def parse_recipes(results):
	recipes = {}
	for item in results['results']:
		recipes[strip_nonalnum(item['title'])] = item['href']
	return recipes

def serialize_ingredients(dict):
	str = ''
	for key, item in dict.iteritems():
		str = str + item + ','
	return str[:-1]

def extract_image_data(item):
	if item['value'] > 0.5:
		return item['name']
	return ''

def strip_nonalnum(word):
    return re.sub(r"^\W+|\W+$", "", word)