import json
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
import os
import subprocess
import sys
import time
# --- DAPR SDK IMPORTS ---
from dapr.clients import DaprClient
#from dapr.clients.grpc._gen.dapr_pb2 import InvokeBindingRequest # Optional, for type hinting if desired
# --- END DAPR SDK IMPORTS ---

# --- CONFIG ---
DB_TABLE = os.getenv("DB_TABLE", "dapr_web") # Table to insert data into
SITEMAP_URL = os.getenv("SITEMAP_URL", "https://docs.dapr.io/en/sitemap.xml") # URL of the sitemap to check for updates
JSON_FILE = os.getenv("JSON_FILE", "dapr_docs_web.json") # Path to the JSON file to load into the database
SCRAPY_TARGET_PATH = os.getenv("SCRAPY_TARGET_PATH", "dapr_docs_web") # Path to the Scrapy project directory

# --- DAPR BINDING & SECRET CONFIG (as defined in your YAMLs) ---
DAPR_BINDING_NAME = os.getenv("DAPR_BINDING_NAME", "pgdb-agents-connection")
DAPR_SECRET_STORE_NAME = os.getenv("DAPR_SECRET_STORE_NAME", "kubernetes") # Typically 'kubernetes' in K8s
DAPR_SECRET_NAME = os.getenv("DAPR_SECRET_NAME", "pg-secret-dapr")
DAPR_SECRET_KEY = os.getenv("DAPR_SECRET_KEY", "connectionString")
# --- END DAPR BINDING & SECRET CONFIG ---

# --- ORIGINAL FUNCTIONS (ADAPTED FOR DAPR SDK) ---

def get_first_sitemap_date(sitemap_url):
    """
    Fetches an XML sitemap and extracts the 'lastmod' date from the first <url> entry.
    (This function remains unchanged as it doesn't interact with Dapr)
    """
    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()

        xml_content = response.content
        root = ET.fromstring(xml_content)
        
        namespaces = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        first_url_element = root.find('s:url', namespaces)

        if first_url_element is not None:
            lastmod_element = first_url_element.find('s:lastmod', namespaces)
            if lastmod_element is not None:
                return lastmod_element.text
            else:
                print("No <lastmod> element found within the first <url>.")
                return None
        else:
            print("No <url> element found in the sitemap.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the sitemap: {e}")
        return None
    except ET.ParseError as e:
        print(f"Error parsing the XML content: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_db_date(db_table):
    """
    Fetches the most recent 'lastupdate' date from the specified database table using Dapr SDK binding.
    """
    with DaprClient() as d:
        # For query operations with bindings, the SQL goes into the metadata.
        # Dapr's PostgreSQL binding typically returns results in a 'result' key.
        # The Dapr SDK's invoke_binding method expects `data` as bytes or dict,
        # and `metadata` as a dictionary.

        sqlCmd = ('SELECT lastupdate FROM {db_table} ORDER BY lastupdate DESC LIMIT 1;'.format(db_table=db_table))
        payload = {'sql': sqlCmd}

        print(sqlCmd, flush=True)

        try:
        # Select using Dapr output binding via HTTP Post
            resp = d.invoke_binding(binding_name=DAPR_BINDING_NAME, operation='query',
                                     binding_metadata=payload)
            print(resp, flush=True)
            result_data = resp.json()
            print("Selected DB result:", result_data, flush=True)
            print("-----------------", flush=True)

            
            # The response data from Dapr SDK is bytes, so decode it and parse JSON
            #result_data = json.loads(resp.data.decode('utf-8'))

            if result_data and 'result' in result_data and len(result_data['result']) > 0:
                #return result_data['result'][0]['lastupdate']
                return result_data['result'][0][0]
            else:
                print("No 'lastupdate' date found in the database.")
                return None
        except Exception as e:
             print(e, flush=True)
             raise SystemExit(e)
           
    
def date_comparison(sitemap_date, db_date):
    # This function remains unchanged
    dt_with_tz = datetime.fromisoformat(sitemap_date)
    dt_pg_date = datetime.strptime(str(db_date), "%Y-%m-%d").date()

    print(f"Original string with timezone: {sitemap_date}")
    print(f"Parsed datetime with timezone: {dt_with_tz} (Type: {type(dt_with_tz)})")
    print(f"Original PostgreSQL date string: {db_date}")
    print(f"Parsed PostgreSQL date: {dt_pg_date} (Type: {type(dt_pg_date)})")

    date_from_tz_string = dt_with_tz.date()

    print(f"\nDate part from string with timezone: {date_from_tz_string}")
    print(f"Date part from PostgreSQL date string: {dt_pg_date}")

    if date_from_tz_string > dt_pg_date:
        print(f"Result: {date_from_tz_string} is AFTER {dt_pg_date}")
        return True
    elif date_from_tz_string < dt_pg_date:
        print(f"Result: {date_from_tz_string} is BEFORE {dt_pg_date}")
        return False
    else:
        print(f"Result: {date_from_tz_string} is the SAME DAY as {dt_pg_date}")
        return False
  
def load_into_db(db_table, JSON_FILE, SCRAPY_TARGET_PATH):
    """
    Function to load data from downloaded json into the database using Dapr SDK binding.
    """
    crawled_json_file = os.path.join(SCRAPY_TARGET_PATH, JSON_FILE)
    
    with open(crawled_json_file, "r") as f:
        docs = json.load(f)

    with DaprClient() as d:
        # DELETE TABLE using Dapr "exec" operation
        print(f"Deleting all records from table '{db_table}' via Dapr SDK...")
        sqlCmd = 'DELETE FROM {db_table};'.format(db_table=db_table)
        payload = {'sql': sqlCmd}

        d.invoke_binding(binding_name=DAPR_BINDING_NAME, operation='exec',
                                     binding_metadata=payload)
        # Note: Dapr SDK does not return a response for 'exec' operations, so we assume success
        print("Database table deleted successfully via Dapr SDK.")


        # INSERT
        today = date.today()

        print("Inserting data into the database via Dapr SDK...")
        for doc in docs:
            url = doc["url"]
            text = doc["text"]
            
            cleaned_text = text.replace('\t', ' ').replace('\n', ' ')
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
            text = cleaned_text

            # INSERT using Dapr "exec" operation with parameters
            # The 'payload' needs to be a dictionary with a 'params' key holding the list of values.
            # Dapr SDK requires data to be JSON-serializable if not bytes.
            
            sqlCmd = (' INSERT INTO %s (url, text, lastupdate) VALUES ' 
                      + '(%s, %s, %s)') % (db_table, f"'{url}'", f"'{text}'", f"'{today}'")
        
            payload = {'sql': sqlCmd}

            print(sqlCmd, flush=True)

            try:
                # Insert order using Dapr output binding via HTTP Post
                resp = d.invoke_binding(binding_name=DAPR_BINDING_NAME,
                                operation='exec',
                                binding_metadata=payload, 
                                data='')
                return resp
            except Exception as e:
                print(e, flush=True)
                raise SystemExit(e)
           
        print("Data loaded into the database successfully via Dapr SDK.")

def exec_scrapy_crawler():
    """
    Function to execute the Scrapy crawl command.
    (This function remains unchanged as it doesn't interact with Dapr)
    """
    try:
        initial_cwd = os.getcwd()

        os.chdir(SCRAPY_TARGET_PATH)
        print(f"Changed current working directory to: {os.getcwd()}")
        
        if os.path.exists(JSON_FILE):
            os.remove(JSON_FILE)
            print(f"Removed existing JSON file: {JSON_FILE}")
        else:
            print(f"JSON file does not exist, will create a new one: {JSON_FILE}")

        subprocess.run(["scrapy", "crawl", "dapr_docs_web", "-o", JSON_FILE], check=True)
        print("Scrapy crawl executed successfully.")

        os.chdir(initial_cwd)
        
    except OSError as e:
        print(f"Error changing directory to '{SCRAPY_TARGET_PATH}': {e}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing Scrapy crawl: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # 0) Wait for 5 minutes before running the pods logic
    WAIT_FOR_PODS = os.getenv("WAIT_FOR_PODS", "True").lower() == "true"
    if WAIT_FOR_PODS:
        print("Waiting for 5 min before running the pods logic...")
        time.sleep(30)
        print("Finished waiting.")

    # Get connection string via Dapr Secrets Building Block using SDK
    try:
        print(f"Attempting to retrieve secret '{DAPR_SECRET_NAME}' from store '{DAPR_SECRET_STORE_NAME}' using key '{DAPR_SECRET_KEY}' via Dapr SDK...")
        with DaprClient() as d:
            secret_response = d.get_secret(DAPR_SECRET_STORE_NAME, DAPR_SECRET_NAME)
            conn_str = secret_response.secret.get(DAPR_SECRET_KEY)
            if conn_str:
                print("Successfully retrieved database connection string via Dapr SDK Secrets (though not directly used by the binding invocation).")
            else:
                print(f"Secret key '{DAPR_SECRET_KEY}' not found in secret '{DAPR_SECRET_NAME}'. Available keys: {secret_response.secret.keys()}", file=sys.stderr)
                sys.exit(1) # Critical error if secret key is missing
    except Exception as e:
        print(f"Failed to retrieve database connection string via Dapr SDK Secrets: {e}", file=sys.stderr)
        sys.exit(1) # Critical error, exit

    # 1) Get the first 'lastmod' date from the sitemap
    sitemap_date = get_first_sitemap_date(SITEMAP_URL)
    if sitemap_date:
        print(f"The 'lastmod' date from the first URL in the sitemap is: {sitemap_date}")
    else:
        print("Could not retrieve the first date from the sitemap.")
        sys.exit(1) # Use sys.exit for consistency
    
    # 2) Check if sitemap.xml date data is more recent or there is no data in table
    # if database date data is older -> do nothing
    db_date = get_db_date(DB_TABLE)
    if db_date:
        print(f"The most recent 'lastupdate' date from the database is: {db_date}")
        if date_comparison(sitemap_date, db_date):
            print("The sitemap date is more recent than the database date, reloading data into the database.")
            exec_scrapy_crawler()
            load_into_db(DB_TABLE, JSON_FILE, SCRAPY_TARGET_PATH)
        else:
            print("The sitemap date is not more recent than the database date, no action taken.")
    else:
        print("Could not retrieve the date from the database, so it is empty (no rows).")
        exec_scrapy_crawler()
        load_into_db(DB_TABLE, JSON_FILE, SCRAPY_TARGET_PATH)
