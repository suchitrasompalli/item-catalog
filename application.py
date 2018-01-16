"""Main application code handling http requests."""
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask import session, flash
import random
import string
import os
import json

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
from flask import make_response
from functools import wraps
import requests

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from database_setup import Base, User, Category, Item
from urlparse import unquote

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

APPLICATION_NAME = "ItemCatalog"

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
db_session = DBSession()


def getCategoryJSON(categories):
    """Helper function builds the json for each of the categories."""
    category_list = []
    for category in categories:
        category_dict = {}
        category_dict['id'] = category.id
        category_dict['name'] = category.name
        items = db_session.query(Item).filter_by(category_id=category.id).all()
        category_dict['Item'] = getItemsJSON(items)
        category_list.append(category_dict)
    return category_list


def getItemsJSON(items):
    """Helper function that builds json for each of the items."""
    items_list = []
    for i in items:
        items_list.append(i.serialize)
    return items_list


@app.route('/catalog.json')
def catalogJSON():
    """Return json showing all the items in each category."""
    categories = db_session.query(Category).all()
    catalog_dict = {}
    catalog_dict['Category'] = getCategoryJSON(categories)
    return jsonify(catalog_dict)


@app.route('/catalog/<int:category_id>/item/JSON')
def categoryItemsJSON(category_id):
    """Get all items based of a single category."""
    items = db_session.query(Item).filter_by(
        category_id=category_id).all()
    return jsonify(Item=[i.serialize for i in items])


@app.route('/catalog/<int:category_id>/item/<int:item_id>/JSON')
def itemJSON(category_id, item_id):
    """Get the item description json for given item."""
    try:
        item = db_session.query(Item).filter_by(id=item_id,
                                                category_id=category_id).one()
        return jsonify(Item=item.serialize)
    except NoResultFound:
        return jsonify({})


@app.route('/categories/JSON')
def categoriesJSON():
    """Get all categories json."""
    categories = db_session.query(Category).all()
    return jsonify(categories=[c.serialize for c in categories])


@app.route('/catalog/<category_name>/item/JSON')
def categoryNameItemsJSON(category_name):
    """Get all items based of a single category identified by name."""
    try:
        category = db_session.query(Category).filter_by(
                                name=category_name).one()
        items = db_session.query(Item).filter_by(category_id=category.id).all()
        return jsonify(Item=[i.serialize for i in items])
    except NoResultFound:
        return jsonify({})


@app.route('/')
@app.route('/catalog/')
def showLatestItems():
    """Show all the categories in catalog and the top ten added items."""
    categories = db_session.query(Category).all()
    items = db_session.query(Item).order_by(desc(Item.id)).limit(10).all()
    return render_template('latest_items.html', categories=categories,
                           items=items)


# Show items in a category
@app.route('/catalog/<category_name>/')
@app.route('/catalog/<category_name>/items/')
def showSpecificCategory(category_name):
    """Show all items for a category."""
    categories = db_session.query(Category).all()
    category = db_session.query(Category).filter_by(name=category_name).one()
    items = db_session.query(Item).filter_by(category=category).all()
    return render_template('specific_category.html', categories=categories,
                           items=items, category_name=category_name)


# Show item description
@app.route('/catalog/<category_name>/<item_name>/')
def showItemDescription(category_name, item_name):
    """Show the item name and its description."""
    item = db_session.query(Item).filter_by(name=item_name).one()
    return render_template('itemdescription.html', item=item)


# Create anti-forgery state token
@app.route('/catalog/login/')
def showLogin():
    """Page to display google login button."""
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for _ in range(32))
    session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """Connect to google authentication to get a access token for user."""
    # Validate state token
    if request.args.get('state') != session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = session.get('access_token')
    stored_gplus_id = session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already \
        connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    session['access_token'] = credentials.access_token
    session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    session['username'] = data['name']
    session['picture'] = data['picture']
    session['email'] = data['email']

    # see if user exists, if not make a new one.
    user_id = getUserID(session['email'])
    if not user_id:
        user_id = createUser(session)
    session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += session['username']
    output += '!</h1>'
    output += '<img src="'
    output += session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: \
    150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % session['username'])
    print("done!")
    return output


# User Helper Functions

def createUser(session):
    """Create User from session data."""
    newUser = User(name=session['username'], email=session[
                   'email'], picture=session['picture'])
    db_session.add(newUser)
    db_session.commit()
    user = db_session.query(User).filter_by(email=session['email']).one()
    return user.id


def getUserInfo(user_id):
    """Get user with user_id."""
    user = db_session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    """Get user whose email identifies them."""
    try:
        user = db_session.query(User).filter_by(email=email).one()
        return user.id
    except NoResultFound:
        return None


@app.route('/gdisconnect')
def gdisconnect():
    """Disconnect user from application and revoke token from googleapis."""
    access_token = session.get('access_token')
    if access_token is None:
        print('Access Token is None')
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print('In gdisconnect access token is ' + access_token)
    print('User name is: ')
    print(session['username'])
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % \
          session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print('result is ')
    print(result)
    if result['status'] == '200':
        del session['access_token']
        del session['gplus_id']
        del session['username']
        del session['email']
        del session['picture']
        del session['user_id']
        flash("You are now logged out.")
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given \
                                             user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


def validForm(name, description):
    """Validate form inputs."""
    if (len(name) == 0) or (len(name) > 25):
        flash("Name field must not be empty or larger than 25 characters")
        return False
    else:
        if (len(description) > 250):
            flash("Description field must not be larger than 250 \
                       characters")
            return False
    return True


def login_required(f):
    """Check if user logged in before further access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/catalog/login')
        else:
            return f(*args, **kwargs)
    return decorated_function


@app.route('/catalog/addItem/', methods=['GET', 'POST'])
@login_required
def addItem():
    """Create a new item under a category."""
    if request.method == 'POST':
        if validForm(request.form["name"], request.form["description"]):
            print("finished valid form")
            newItem = Item(name=request.form["name"],
                           description=request.form["description"],
                           category_id=request.form['select'],
                           user_id=session['user_id'])
            db_session.add(newItem)
            db_session.commit()
            flash('New Item Successfully Created')
            return redirect(url_for('showLatestItems'))
        else:
            flash("failed add. Check data")
            categories = db_session.query(Category).all()
            return render_template('addItem.html', categories=categories)
    else:
        categories = db_session.query(Category).all()
        return render_template('addItem.html', categories=categories)


@app.route('/catalog/<item_name>/edit/', methods=['GET', 'POST'])
@login_required
def editItem(item_name):
    """Make changes to existing Item in database."""
    item_name = unquote(item_name)
    itemToEdit = db_session.query(Item).filter_by(name=item_name).one()
    if session['user_id'] != itemToEdit.user_id:
        return "<script>function myFunction() {alert('You are not authorized \
         to edit this item.  Please create your own items to edit them.');}\
         </script><body onload='myFunction()'>"
    if request.method == 'POST':
        if validForm(request.form["name"], request.form["description"]):
            if request.form['name']:
                itemToEdit.name = request.form["name"]
            if request.form['description']:
                itemToEdit.description = request.form["description"]
            if request.form['select']:
                itemToEdit.category_id = request.form['select']
            db_session.add(itemToEdit)
            db_session.commit()
            flash('Item Successfully Edited')
            return redirect(url_for('showLatestItems'))
        else:
            categories = db_session.query(Category).all()
            return render_template('editItem.html', categories=categories,
                                   item=itemToEdit)
    else:
        categories = db_session.query(Category).all()
        return render_template('editItem.html', categories=categories,
                               item=itemToEdit)


# Edit a item under a category.
@app.route('/catalog/<item_name>/delete/', methods=['GET', 'POST'])
@login_required
def deleteItem(item_name):
    """Delete a item in database."""
    itemToDelete = db_session.query(Item).filter_by(name=item_name).one()
    if session['user_id'] != itemToDelete.user_id:
        return "<script>function myFunction() {alert('You are not authorized \
         to delete this item.  Please create your own items to delete \
         them.'); }</script><body onload='myFunction()'>"
    if request.method == 'POST':
        db_session.delete(itemToDelete)
        db_session.commit()
        flash('Item Successfully Deleted')
        return redirect(url_for('showLatestItems'))
    else:
        return render_template('deleteItem.html')


if __name__ == '__main__':
    app.secret_key = os.urandom(24)
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
