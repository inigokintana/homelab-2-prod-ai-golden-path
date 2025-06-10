import json
import psycopg2
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
import os
import subprocess
import sys # To exit gracefully on critical errors

# --- CONFIG ---
#DB_URL = "postgresql+psycopg2://postgres:pgvector@localhost:15432/postgres"
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "pgvector",
    "host": "localhost",
    "port": 15432,
}
DB_TABLE = "dapr_web"  # Table to insert data into
SITEMAP_URL = "https://docs.dapr.io/en/sitemap.xml" # URL of the sitemap to check for updates
JSON_FILE = "dapr_docs_web.json"  # Path to the JSON file to load into the database
SCRAPY_TARGET_PATH = "dapr_docs_web"  # Path to the Scrapy project directory

# --- END CONFIG ---

####
# This script checks the 'lastmod' date from a sitemap.xml file against the most recent 'lastupdate' date in a PostgreSQL database.
# If the sitemap date is more recent, it truncates the table and reloads data from a JSON file.
####

# get date data from sitemap.xml
def get_first_sitemap_date(sitemap_url):
    """
    Fetches an XML sitemap and extracts the 'lastmod' date from the first <url> entry.

    Args:
        sitemap_url (str): The URL of the sitemap.xml file.

    Returns:
        str: The 'lastmod' date as a string, or None if not found or an error occurs.
    """
    try:
        # 1. Fetch the sitemap.xml content
        response = requests.get(sitemap_url, timeout=10) # Added a timeout for robustness
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        xml_content = response.content

        # 2. Parse the XML
        # Use a namespace-aware parser. Sitemaps typically use the
        # 'http://www.sitemaps.org/schemas/sitemap/0.9' namespace.
        root = ET.fromstring(xml_content)
        
        # Define the namespace dictionary
        namespaces = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        # 3. Find the first <url> element using XPath with namespace
        first_url_element = root.find('s:url', namespaces)

        if first_url_element is not None:
            # 4. Extract the text from the <lastmod> child element
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

# get date from db
def get_db_date(db_config, db_table):

    """
    Fetches the most recent 'lastmod' date from the specified database table.

    Args:
        db_config (dict): Database connection configuration.
        db_table (str): The name of the table to query.

    Returns:
        str: The most recent 'lastmod' date as a string, or None if not found or an error occurs.
    """
    try:
        # Connect to the database
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Query to get the most recent 'lastmod' date
        cursor.execute(f"SELECT lastupdate FROM {db_table} ORDER BY lastupdate DESC LIMIT 1;")
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return result[0]  # Assuming 'lastupdate' is the first column in the result
        else:
            print("No 'lastupdate' date found in the database.")
            return None

    except Exception as e:
        print(f"An error occurred while fetching the date from the database: {e}")
        exit(1)
    
# Compare date from sitemap with date in db    
def date_comparison(sitemap_date, db_date):

    # Date strings you want to compare
    # date_string_with_timezone = "2025-06-03T15:58:08+02:00"
    # postgresql_date_string = "2025-06-02"

    # --- Step 1: Convert the string with timezone to a datetime object ---
    # datetime.fromisoformat() is excellent for ISO 8601 format strings,
    # including those with timezone information.
    dt_with_tz = datetime.fromisoformat(sitemap_date)

    # --- Step 2: Convert the PostgreSQL date string to a date object ---
    # datetime.strptime() is used to parse a string into a datetime object
    # based on a specified format.
    # We then extract just the date part.
    dt_pg_date = datetime.strptime(str(db_date), "%Y-%m-%d").date()

    print(f"Original string with timezone: {sitemap_date}")
    print(f"Parsed datetime with timezone: {dt_with_tz} (Type: {type(dt_with_tz)})")
    print(f"Original PostgreSQL date string: {db_date}")
    print(f"Parsed PostgreSQL date: {dt_pg_date} (Type: {type(dt_pg_date)})")

    # --- Step 3: Perform the comparison ---
    # For fair comparison, we'll compare their date components.
    # The .date() method on a datetime object returns just the date part (year, month, day).
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
    # --- END DATE COMPARISON ---
  
def load_into_db(DB_CONFIG, DB_TABLE, JSON_FILE, SCRAPY_TARGET_PATH):
    """
    Function to load data from downloaded json into the database.
    pgai vectorizer will do the chunck splitting as well, no need to do it here
    """
    crawled_json_file= os.path.join(SCRAPY_TARGET_PATH, JSON_FILE)
    # --- LOAD DATA ---
    with open(crawled_json_file, "r") as f:
        docs = json.load(f)

    # --- DB CONNECTION ---
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute(f"delete from {DB_TABLE};")
    conn.commit()
    print("Database table deleted successfully.")

    today = date.today()

    for doc in docs:
        url = doc["url"]
        text = doc["text"]
        # cleaning \n \t with spaces 
        cleaned_text = text.replace('\t', ' ').replace('\n', ' ')
        # cleaning spaces
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        text = cleaned_text

        cursor.execute(f"""
            INSERT INTO {DB_TABLE} (url, text, lastupdate)
            VALUES (%s, %s, %s)
        """, (url, text,today))

    conn.commit()
    cursor.close()
    conn.close()
    print("Data loaded into the database successfully.")

    # --- END LOAD DATA ---

def exec_scrapy_crawler():
    """
    Function to execute the Scrapy crawl command.

    Scrappy project is created in Dockerfile, so it is not necessary to run scrapy startproject dapr_docs_web
    It assumes that the Scrapy project is already set up in the specified directory.    
    It changes the current working directory to the Scrapy project directory,
    executes the Scrapy crawl command, and then changes back to the original directory.
    It will save the output to a JSON file specified by the JSON_FILE variable.
    If the directory change or Scrapy command fails, it will print an error message and exit the script.
    This function is intended to be called after checking the sitemap date against the database date.
    It will not run if the database date is more recent than the sitemap date.
    It will also run if the database is empty.
    """
    try:
        #initial directory
        initial_cwd = os.getcwd()

        # Change to the target directory
        os.chdir(SCRAPY_TARGET_PATH)
        print(f"Changed current working directory to: {os.getcwd()}")
        
        # Check if the JSON file already exists and remove it
        if os.path.exists(JSON_FILE):
            os.remove(JSON_FILE)
            print(f"Removed existing JSON file: {JSON_FILE}")
        else:
            print(f"JSON file does not exist, will create a new one: {JSON_FILE}")

        # Execute the Scrapy crawl command
        subprocess.run(["scrapy", "crawl", "dapr_docs_web", "-o", JSON_FILE], check=True)
        print("Scrapy crawl executed successfully.")

        # Change back to the initial directory
        os.chdir(initial_cwd)
        
    except OSError as e:
        print(f"Error changing directory to '{SCRAPY_TARGET_PATH}': {e}", file=sys.stderr)
        sys.exit(1)  # Exit if changing directory fails
    except subprocess.CalledProcessError as e:
        print(f"Error executing Scrapy crawl: {e}", file=sys.stderr)
        sys.exit(1)  # Exit if the Scrapy command fails

if __name__ == "__main__":
    # 1) Get the first 'lastmod' date from the sitemap
    sitemap_date = get_first_sitemap_date(SITEMAP_URL)
    if sitemap_date:
        print(f"The 'lastmod' date from the first URL in the sitemap is: {sitemap_date}")
    else:
        print("Could not retrieve the first date from the sitemap.")
        exit(1)
    
    # 2) if sitemap.xml date data is more recent or there is no data in table, -> truncate table and load everything again
    # if database date data is older -> do nothing
    db_date = get_db_date(DB_CONFIG, DB_TABLE)
    if db_date:
        print(f"The most recent 'lastupdate' date from the database is: {db_date}")
        if date_comparison(sitemap_date, db_date):
            print("The sitemap date is more recent than the database date, reloading data into the database.")
            # cd dapr_docs_web ; scrapy crawl dapr_docs_web -o dapr_docs_web.json
            exec_scrapy_crawler()
            load_into_db(DB_CONFIG, DB_TABLE,JSON_FILE, SCRAPY_TARGET_PATH)
        else:
            print("The sitemap date is not more recent than the database date, no action taken.")
    else:
        print("Could not retrieve the date from the database, so it is empty no rows .")
        # cd dapr_docs_web ; scrapy crawl dapr_docs_web -o dapr_docs_web.json
        exec_scrapy_crawler()
        load_into_db(DB_CONFIG, DB_TABLE,JSON_FILE, SCRAPY_TARGET_PATH)