# Item Catalog Website
The Item Catalog web application provides a list of items within a variety of
categories.
It also provides a user registration and authentication system.

## How to setup and launch the program.
1. Obtain OAuth credentials from (https://developers.google.com/identity/protocols/OAuth2)

2. Go to your app's page in the Google APIs Console — (https://console.developers.google.com/apis)

3. Choose Credentials from the menu on the left.

4. Create an OAuth Client ID.
This will require you to configure the consent screen.

5. When you're presented with a list of application types, choose Web application.

6. You can then set the authorized JavaScript origins.

7. You will then be able to get the client ID and client secret.
Replace the client_secrets.json  with yours.

Next, set up the initial SQLite database by executing the python script.
 *** python database_setup.py ***

Load the database with initial set of values by executing the python script.
*** python add_catalog_items.py***

Finally run the web application.
   *** python application.py***

Access and test the application by visiting,
*** http://localhost:5000 ***
