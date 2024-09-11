import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from bs4 import BeautifulSoup
import csv

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def wait_and_click(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
        element.click()
        return True
    except (TimeoutException, ElementClickInterceptedException) as e:
        logging.error(f"Failed to click element {value}: {str(e)}")
        return False

def scrape_property_data(url, max_pages=10):
    properties = []
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logging.info("ChromeDriver initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize ChromeDriver: {str(e)}")
        return properties
    
    try:
        logging.info(f"Navigating to {url}")
        driver.get(url)
        
        # Wait for page to load completely
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Check if we're redirected to a different page (potential anti-bot measure)
        if "nigeriapropertycentre.com" not in driver.current_url:
            logging.error(f"Redirected to unexpected URL: {driver.current_url}")
            return properties
        
        # Set search options
        if not wait_and_click(driver, By.ID, "for-rent-tab"):
            logging.error("Failed to click 'For Rent' tab")
            return properties
        
        location_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "search-location")))
        location_input.clear()
        location_input.send_keys("Lekki, Lagos")
        logging.info("Entered location: Lekki, Lagos")
        
        select_options = {
            "search-type": "Flat / Apartment",
            "search-bedrooms": "1",
            "search-max-price": "₦ 10 Million",
            "search-furnishing": "Furnished",
            "search-serviced": "Serviced"
        }
        
        for select_id, option_text in select_options.items():
            try:
                Select(WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, select_id)))).select_by_visible_text(option_text)
                logging.info(f"Selected {option_text} for {select_id}")
            except Exception as e:
                logging.error(f"Failed to select {option_text} for {select_id}: {str(e)}")
        
        if not wait_and_click(driver, By.CSS_SELECTOR, "button[type='submit']"):
            logging.error("Failed to click submit button")
            return properties
        
        # Wait for search results
        try:
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "property-list")))
            logging.info("Search results loaded")
        except TimeoutException:
            logging.error("Timeout waiting for search results")
            logging.debug(f"Current page source: {driver.page_source}")
            return properties
        
        page = 1
        while page <= max_pages:
            logging.info(f"Scraping page {page}")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            listings = soup.find_all('div', class_='property-list-item')
            
            if not listings:
                logging.warning(f"No listings found on page {page}. Ending search.")
                break
            
            for listing in listings:
                title = listing.find('h4', class_='property-title')
                price = listing.find('span', class_='price')
                location = listing.find('address')
                
                if title and price and location:
                    properties.append({
                        'Title': title.text.strip(),
                        'Price': price.text.strip(),
                        'Location': location.text.strip()
                    })
            
            logging.info(f"Scraped {len(listings)} listings from page {page}")
            
            next_page = soup.find('a', class_='next')
            if next_page and page < max_pages:
                next_url = next_page['href']
                logging.info(f"Navigating to next page: {next_url}")
                driver.get(next_url)
                time.sleep(5)  # Wait for page to load
                page += 1
            else:
                logging.info("No more pages to scrape")
                break
    
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        logging.debug(f"Current page source: {driver.page_source}")
    
    finally:
        driver.quit()
    
    return properties

def save_to_csv(properties, filename='lekki_apartments.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['Title', 'Price', 'Location'])
        writer.writeheader()
        for prop in properties:
            writer.writerow(prop)
    logging.info(f"Saved {len(properties)} properties to {filename}")

if __name__ == "__main__":
    base_url = "https://nigeriapropertycentre.com/"
    scraped_data = scrape_property_data(base_url)
    save_to_csv(scraped_data)
    print(f"Scraped {len(scraped_data)} properties and saved to lekki_apartments.csv")