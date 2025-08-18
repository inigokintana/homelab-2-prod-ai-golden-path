import json
import logging
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
# --- END DAPR SDK IMPORTS ---

# ---------------------------------------------------
# Configure logging from environment variable
# ---------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Map string to logging level (default INFO if invalid)
LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
log_level = LEVELS.get(LOG_LEVEL, logging.INFO)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)
# ---------------------------------------------------

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
                logger.warning("No <lastmod> element found within the first <url> in the sitemap.")
                return None
        else:
            logger.warning("No <url> element found in the sitemap.")    
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching the sitemap: {e}")
        return None
    except ET.ParseError as e:
        logger.error(f"Error parsing the XML content: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
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

        logger.info(f"Querying the database for the most recent 'lastupdate' date via Dapr SDK: {sqlCmd}")

        try:
        # Select using Dapr output binding via HTTP Post
            resp = d.invoke_binding(binding_name=DAPR_BINDING_NAME, operation='query',
                                     binding_metadata=payload)
            logger.debug(f"Response from Dapr binding query: {resp}")
            result_data = resp.json()
            logger.debug(f"Selected DB result: {result_data}")
            logger.debug(f"Selected DB result date: {result_data[0][0]}")
            logger.debug("-----------------")

            # Check if the result contains data
            if result_data[0][0]:
                return result_data[0][0]
            else:
                logger.warning("No 'lastupdate' date found in the database.")
                return None
        except Exception as e:
             logger.error(f"An error occurred while querying the database: {e}")
             raise SystemExit(e)
           
    
def date_comparison(sitemap_date, db_date):
    # This function remains unchanged
    dt_with_tz = datetime.fromisoformat(sitemap_date)
    # dt_pg_date = datetime.strptime(str(db_date), "%Y-%m-%d").date()
    dt_pg_date = datetime.fromisoformat(db_date)

    logger.info(f"Original string with timezone: {sitemap_date}")  
    logger.info(f"Parsed datetime with timezone: {dt_with_tz} (Type: {type(dt_with_tz)})")  
    logger.info(f"Original PostgreSQL date string: {db_date}")
    logger.info(f"Parsed PostgreSQL date: {dt_pg_date} (Type: {type(dt_pg_date)})")

    date_from_tz_string = dt_with_tz.date()
    dt_pg_date_string = dt_pg_date.date()

    logger.info(f"Date part from string with timezone: {date_from_tz_string}")
    logger.info(f"Date part from PostgreSQL date string: {dt_pg_date_string}")

    if date_from_tz_string > dt_pg_date_string:
        logger.info(f"Result: {date_from_tz_string} is AFTER {dt_pg_date_string}")
        return True
    elif date_from_tz_string < dt_pg_date_string:
        logger.info(f"Result: {date_from_tz_string} is BEFORE {dt_pg_date_string}")
        return False
    else:
        logger.info(f"Result: {date_from_tz_string} is the SAME DAY as {dt_pg_date_string}")
        return False
  
def load_into_db(db_table, JSON_FILE, SCRAPY_TARGET_PATH):
    """
    Function to load data from downloaded json into the database using Dapr SDK binding.
    """
    crawled_json_file = os.path.join(SCRAPY_TARGET_PATH, JSON_FILE)
    
    with open(crawled_json_file, "r") as f:
        docs = json.load(f)

    with DaprClient() as d:
        # 1) DELETE TABLE using Dapr "exec" operation
        logger.info(f"Deleting all records from table '{db_table}' via Dapr SDK...")
        sqlCmd = 'DELETE FROM {db_table};'.format(db_table=db_table)
        payload = {'sql': sqlCmd}

        d.invoke_binding(binding_name=DAPR_BINDING_NAME, operation='exec',
                                     binding_metadata=payload)
        # Note: Dapr SDK does not return a response for 'exec' operations, so we assume success
        logger.info(f"Database table '{db_table}' deleted successfully via Dapr SDK.")


        # 2) INSERT
        today = date.today()
        logger.info("Inserting data into the database via Dapr SDK...")
        for doc in docs:
            url = doc["url"]
            text = doc["text"]
            
            cleaned_text = text.replace('\t', ' ').replace('\n', ' ')
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
            text = cleaned_text

            # INSERT using Dapr "exec" operation with parameters
            # The 'payload' needs to be a dictionary with a 'params' key holding the list of values.
            # Dapr SDK requires data to be JSON-serializable if not bytes.
            
            sqlCmd = f"INSERT INTO {db_table} (url, text, lastupdate) VALUES ($1, $2, $3);"

            # Prepare the parameters as a list
            params = [url, text, today.isoformat()]
            # Prepare the payload for Dapr binding
            logger.debug(f"SQL Command: {sqlCmd}")

            try:
                # Insert order using Dapr output binding via HTTP Post
                d.invoke_binding(binding_name=DAPR_BINDING_NAME,
                            operation='exec',
                            data=json.dumps({"sql": sqlCmd, "params": params}).encode('utf-8'), # Data must be bytes or dict
                            binding_metadata={'sql': sqlCmd, 'params': json.dumps(params)}) # Deprecated but often still needed for binding specific context
            except Exception as e:
                logger.error(f"An error occurred while inserting data into the database: {e}")
                # If an error occurs, we raise SystemExit to stop the script
                raise SystemExit(e)
           
        logger.info("Data loaded into the database successfully via Dapr SDK.")

def exec_scrapy_crawler():
    """
    Function to execute the Scrapy crawl command.
    (This function remains unchanged as it doesn't interact with Dapr)
    """
    try:
        initial_cwd = os.getcwd()

        os.chdir(SCRAPY_TARGET_PATH)
        logger.info(f"Changed current working directory to: {os.getcwd()}")
        
        if os.path.exists(JSON_FILE):
            os.remove(JSON_FILE)
            logger.info(f"Removed existing JSON file: {JSON_FILE}")
        else:
            logger.info(f"JSON file does not exist, will create a new one: {JSON_FILE}")

        subprocess.run(["scrapy", "crawl", "dapr_docs_web", "-o", JSON_FILE], check=True)
        logger.info("Scrapy crawl executed successfully.")

        os.chdir(initial_cwd)
        
    except OSError as e:
        logger.error(f"Error changing directory to '{SCRAPY_TARGET_PATH}': {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing Scrapy crawl: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 0) Wait for 30 seconds before running the pods logic
    WAIT_FOR_PODS = os.getenv("WAIT_FOR_PODS", "True").lower() == "true"
    if WAIT_FOR_PODS:
        logger.info("Waiting for 30 seconds before running the pods logic...")
        time.sleep(30)
        logger.info("Finished waiting.")    

    # 1) Check we can get connection string via Dapr Secrets Building Block using SDK - Although not directly used by the binding invocation, it is a good practice to ensure the secret is available.
    # This is to ensure that the Dapr sidecar is running and the secret store is configured correctly.
    # If the secret is not available, the binding invocation will fail, so we check it upfront.
    try:
        logger.info(f"Attempting to retrieve secret '{DAPR_SECRET_NAME}' from store '{DAPR_SECRET_STORE_NAME}' using key '{DAPR_SECRET_KEY}' via Dapr SDK...")
        with DaprClient() as d:
            secret_response = d.get_secret(DAPR_SECRET_STORE_NAME, DAPR_SECRET_NAME)
            conn_str = secret_response.secret.get(DAPR_SECRET_KEY)
            if conn_str:
                logger.info("Successfully retrieved database connection string via Dapr SDK Secrets (though not directly used by the binding invocation).")
            else:
                logger.error(f"Secret key '{DAPR_SECRET_KEY}' not found in secret '{DAPR_SECRET_NAME}'. Available keys: {secret_response.secret.keys()}")   
                sys.exit(1) # Critical error if secret key is missing
    except Exception as e:
        logger.error(f"Failed to retrieve database connection string via Dapr SDK Secrets: {e}")
        sys.exit(1) # Critical error, exit

    # 2) Get the first 'lastmod' last modification date from the sitemap in Dapr URL
    sitemap_date = get_first_sitemap_date(SITEMAP_URL)
    if sitemap_date:
        logger.info(f"The 'lastmod' date from the first URL in the sitemap is: {sitemap_date}")
        # Convert the date string to a datetime object for comparison
    else:
        logger.error("Could not retrieve the first date from the sitemap.")
        sys.exit(1) # Use sys.exit for consistency
    
    # 3) Check if sitemap.xml date data is more recent than in the database or there is no data in database table
    # if database date data is older -> do nothing
    db_date = get_db_date(DB_TABLE)
    if db_date:
        logger.info(f"The most recent 'lastupdate' date from the database is: {db_date}")   
        if date_comparison(sitemap_date, db_date):
            logger.info("The sitemap date is more recent than the database date, reloading data into the database.")
            # 3.1) Execute Scrapy crawler to get the latest data
            exec_scrapy_crawler()
            load_into_db(DB_TABLE, JSON_FILE, SCRAPY_TARGET_PATH)
        else:
            logger.info("The sitemap date is not more recent than the database date, no action taken.")
    else:
        logger.info("Could not retrieve the date from the database, so database is empty (no rows).")
        exec_scrapy_crawler()
        load_into_db(DB_TABLE, JSON_FILE, SCRAPY_TARGET_PATH)

    # 4) Dapr sidecar MUST BE shutdown after the cronjob has finished successfully, see https://docs.dapr.io/operations/hosting/kubernetes/kubernetes-job/
    # Shutdown the Dapr sidecar gracefully
    logger.info("Shutting down Dapr sidecar gracefully...")
    d.close() # Close the Dapr client connection
    try:
        response = requests.post("http://localhost:3500/v1.0/shutdown")
        if response.status_code == 204:
            logger.info("Dapr sidecar shutdown requested successfully.")
        else:
            logger.error(f"Failed to shutdown Dapr sidecar. Status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error during Dapr shutdown request: {e}")
    
    sys.exit(0) # IMPORTANT: Exit with 0 for success
