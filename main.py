import json
import re
import asyncio
from typing import Dict, Any, Optional, List

import httpx
from bs4 import BeautifulSoup
from lxml import etree
from pydantic import BaseModel, Field
from litestar import Litestar, post
from litestar.response import Response


class PriceRequestSource(BaseModel):
    """Model for source URLs to fetch prices from."""
    mrmed: Optional[str] = None
    medkart: Optional[str] = None
    apollo: Optional[str] = None
    netmeds: Optional[str] = None
    pharmeasy: Optional[str] = None
    tata1mg: Optional[str] = None
    truemeds: Optional[str] = None


class PriceRequest(BaseModel):
    """Model for the price request payload."""
    source: PriceRequestSource
    pincode: str
    city: str


class PriceResponse(BaseModel):
    """Model for the price response."""
    mrmed: Optional[Dict[str, Any]] = None
    medkart: Optional[Dict[str, Any]] = None
    apollo: Optional[Dict[str, Any]] = None
    netmeds: Optional[Dict[str, Any]] = None
    pharmeasy: Optional[Dict[str, Any]] = None
    tata1mg: Optional[Dict[str, Any]] = None
    truemeds: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)


from litestar import get, Litestar

@get("/")  # Handles GET (and HEAD by virtue of GET)
def health_check() -> dict[str, str]:
    return {"status": "alive"}

async def fetch_apollo_price(url: str) -> Dict[str, Any]:
    """Fetch the retail price from Apollo Pharmacy."""
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://www.apollopharmacy.in/",
        "Sec-CH-UA": '"Brave";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        ),
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()  
            
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tag = soup.find(
                "script",
                {
                    "class": "structured-data-list",
                    "type": "application/ld+json"
                }
            )
            
            if not script_tag:
                raise ValueError("No <script class='structured-data-list' type='application/ld+json'> tag found")
            
            raw_json = script_tag.string or script_tag.get_text()
            if not raw_json.strip():
                raise ValueError("Empty script content")
                
            data = json.loads(raw_json)
            
            # Safely access nested data
            if not isinstance(data, dict):
                raise ValueError(f"Expected dictionary data, got {type(data)}")
                
            offers = data.get('offers')
            if not offers:
                raise ValueError("No 'offers' field in data")
                
            if not isinstance(offers, dict):
                raise ValueError(f"Expected dictionary for 'offers', got {type(offers)}")
                
            retail_price = offers.get('price')
            if retail_price is None:
                raise ValueError("No 'price' field in offers")
            
            return {
                "url": url,
                "price": retail_price,
                "currency": "INR",
                "source": "apollo"
            }
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Apollo HTTP error: {e.response.status_code} - {e.response.reason_phrase}")
    except httpx.RequestError as e:
        raise ValueError(f"Apollo request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Apollo invalid JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"Apollo price fetch error: {str(e)}")


async def fetch_medkart_price(url: str) -> Dict[str, Any]:
    """Fetch the retail price from Medkart."""
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://www.google.com/",
        "Sec-CH-UA": '"Brave";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        )
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tag = soup.find("script", {"type": "application/ld+json"})
            
            if not script_tag:
                raise ValueError("No script tag with type 'application/ld+json' found")
                
            raw_json = script_tag.string
            if not raw_json or not raw_json.strip():
                raise ValueError("Empty script content")
                
            data = json.loads(raw_json)
            
            # Safely access nested data
            if not isinstance(data, dict):
                raise ValueError(f"Expected dictionary data, got {type(data)}")
                
            offers = data.get('offers')
            if not offers:
                raise ValueError("No 'offers' field in data")
                
            if not isinstance(offers, dict):
                raise ValueError(f"Expected dictionary for 'offers', got {type(offers)}")
                
            retail_price = offers.get('price')
            if retail_price is None:
                raise ValueError("No 'price' field in offers")
            
            return {
                "url": url,
                "price": retail_price,
                "currency": "INR",
                "source": "medkart"
            }
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Medkart HTTP error: {e.response.status_code} - {e.response.reason_phrase}")
    except httpx.RequestError as e:
        raise ValueError(f"Medkart request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Medkart invalid JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"Medkart price fetch error: {str(e)}")


async def fetch_mrmed_price(url: str) -> Dict[str, Any]:
    """Fetch the retail price from MrMed."""
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.5",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-CH-UA": '"Brave";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        )
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            
            if not script_tag:
                raise ValueError("No script tag with id '__NEXT_DATA__' found")
                
            raw_json = script_tag.string
            if not raw_json or not raw_json.strip():
                raise ValueError("Empty script content")
                
            data = json.loads(raw_json)
            
            # Safely navigate through nested data
            props = data.get('props')
            if not props:
                raise ValueError("No 'props' field in data")
                
            page_props = props.get('pageProps')
            if not page_props:
                raise ValueError("No 'pageProps' field in props")
                
            product = page_props.get('product')
            if not product:
                raise ValueError("No 'product' field in pageProps")
                
            retail_price = product.get('priceToCustomer')
            if retail_price is None:
                raise ValueError("No 'priceToCustomer' field in product")
            
            return {
                "url": url,
                "price": retail_price,
                "currency": "INR",
                "source": "mrmed"
            }
    except httpx.HTTPStatusError as e:
        raise ValueError(f"MrMed HTTP error: {e.response.status_code} - {e.response.reason_phrase}")
    except httpx.RequestError as e:
        raise ValueError(f"MrMed request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"MrMed invalid JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"MrMed price fetch error: {str(e)}")


async def fetch_netmeds_price(url: str) -> Dict[str, Any]:
    """Fetch the retail price from Netmeds."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    }
    
    def clean_price(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        # Remove common rupee indicators (₹ or Rs, case-insensitive, optional dot/space)
        text = re.sub(r'(?i)rs\.?\s*', '', text)
        # Remove any character that is not digit or dot
        return re.sub(r'[^\d.]', '', text).strip()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            mrp = ""
            retail_price = ""
            
            # Try multiple approaches to find the price
            # Approach 1: Find the price-box div
            price_box = soup.find('div', class_='price-box')
            if price_box:
                # Extract retail price (final price)
                final_price_span = price_box.find('span', class_='final-price')
                if final_price_span:
                    raw = final_price_span.get_text(strip=True)
                    retail_price = clean_price(raw)
                    
                # Extract MRP
                price_span = price_box.find('span', class_='price')
                if price_span:
                    strike_tag = price_span.find('strike')
                    if strike_tag:
                        raw = strike_tag.get_text(strip=True)
                        mrp = clean_price(raw)
            
            # Approach 2: Try alternative price elements if first approach fails
            if not retail_price:
                # Look for any element with 'price' in class
                price_elements = soup.select('[class*="price"]:not([class*="old"]):not([class*="mrp"])')
                for element in price_elements:
                    text = element.get_text(strip=True)
                    if text:
                        retail_price = clean_price(text)
                        break
            
            if not retail_price:
                raise ValueError("Could not find retail price on Netmeds page")
                
            try:
                # Ensure price is numeric
                float(retail_price)
            except ValueError:
                raise ValueError(f"Invalid price format: {retail_price}")
                
            return {
                "url": url,
                "price": retail_price,
                "mrp": mrp if mrp else None,
                "currency": "INR",
                "source": "netmeds"
            }
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Netmeds HTTP error: {e.response.status_code} - {e.response.reason_phrase}")
    except httpx.RequestError as e:
        raise ValueError(f"Netmeds request failed: {str(e)}")
    except Exception as e:
        raise ValueError(f"Netmeds price fetch error: {str(e)}")

# ---- Fixed Tata1mg function ----
async def fetch_tata1mg_price(url: str, city: str) -> Dict[str, Any]:
    """Fetch the retail price from Tata 1mg."""
    headers = {
        "Host": "www.1mg.com",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.6",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        ),
        "Cookie": (
            f"city={city};"
        ),
        "Priority": "u=0, i",
        "Sec-CH-UA": '"Brave";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1",
    }
    
    def normalize_preloaded_state(data):
        """Properly normalize PRELOADED_STATE that may contain JSON strings."""
        normalized = []
        for item in data:
            if isinstance(item, str):
                # decode the inner JSON string
                try:
                    normalized.append(json.loads(item))
                except json.JSONDecodeError:
                    normalized.append(item)
            else:
                normalized.append(item)
        return normalized
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # First attempt: try to extract from PRELOADED_STATE
            drug_price = None
            errors = []
            
            try:
                script_tag = soup.find(
                    "script",
                    text=re.compile(r"^\s*window\.PRELOADED_STATE\s*=")
                )
                
                if not script_tag or not script_tag.string:
                    raise ValueError("Couldn't find PRELOADED_STATE script or script is empty")
                    
                js_text = script_tag.string
                json_str = re.sub(r"^\s*window\.PRELOADED_STATE\s*=\s*", "", js_text)
                json_str = re.sub(r";\s*$", "", json_str)
                
                data = json.loads(json_str)
                # Apply normalization just like in your practice code
                data = normalize_preloaded_state(data)
                
                # Try each path separately with specific error handling for each
                try:
                    drug_price = data[0]['drugPage']['drugInfo']['sku']['discountedPrice']
                    if drug_price is not None:
                        print(f"Found price at path 1: {drug_price}")
                except (KeyError, IndexError, TypeError) as e:
                    errors.append(f"Path 1 failed: {str(e)}")
                
                if drug_price is None:
                    try:
                        drug_price = data[0]['drugPage']['drugInfo']['care_plan_info_v2']['data'][0]['discount']['price']
                        if drug_price is not None:
                            print(f"Found price at path 2: {drug_price}")
                    except (KeyError, IndexError, TypeError) as e:
                        errors.append(f"Path 2 failed: {str(e)}")
                
                if drug_price is None:
                    try:
                        drug_price = data[0]['otcPage']['otcInfo']['skus']['discountedPrice']
                        if drug_price is not None:
                            print(f"Found price at path 3: {drug_price}")
                    except (KeyError, IndexError, TypeError) as e:
                        errors.append(f"Path 3 failed: {str(e)}")
                
                if drug_price is None:
                    try:
                        drug_price = data[0]['drugPage']['drugInfo']['sku']['price']
                        if drug_price is not None:
                            print(f"Found price at path 4: {drug_price}")
                    except (KeyError, IndexError, TypeError) as e:
                        errors.append(f"Path 4 failed: {str(e)}")
            except Exception as e:
                errors.append(f"PRELOADED_STATE extraction failed: {str(e)}")
                print(f"PRELOADED_STATE extraction error: {str(e)}")
            
            # Second attempt: try to extract from price elements in HTML
            if drug_price is None:
                try:
                    price_selectors = [
                        'span.PriceBoxPriceSection__offer-price-cp',
                        'span[class*="price"]',
                        'div[class*="price"]'
                    ]
                    
                    for selector in price_selectors:
                        price_elements = soup.select(selector)
                        if price_elements:
                            price_text = price_elements[0].get_text(strip=True)
                            # Extract digits and decimal
                            price = re.sub(r'[^\d.]', '', price_text)
                            if price:
                                drug_price = price
                                print(f"Found price in HTML: {drug_price}")
                                break
                except Exception as e:
                    errors.append(f"HTML price extraction failed: {str(e)}")
                    print(f"HTML extraction error: {str(e)}")
            
            if drug_price is None:
                raise ValueError(f"Could not find price in Tata 1mg data: {', '.join(errors)}")
                
            try:
                # Ensure price is numeric
                float(drug_price)
            except ValueError:
                raise ValueError(f"Invalid price format: {drug_price}")
                
            return {
                "url": url,
                "price": drug_price,
                "currency": "INR",
                "source": "tata1mg"
            }
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Tata 1mg HTTP error: {e.response.status_code} - {e.response.reason_phrase}")
    except httpx.RequestError as e:
        raise ValueError(f"Tata 1mg request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Tata 1mg invalid JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"Tata 1mg price fetch error: {str(e)}")


# ---- Fixed PharmEasy function ----
async def fetch_pharmeasy_price(url: str, pincode: str) -> Dict[str, Any]:
    """Fetch the retail price from PharmEasy."""
    headers = {
        "Host": "pharmeasy.in",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36",
        "Cookie": (
            f"X-Default-City=927; X-Pincode={pincode};"
        ),
        "Priority": "u=0, i",
        "Sec-CH-UA": '"Brave";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            # Save HTML content for debugging purposes
            html_content = response.text
            
            # Use both BeautifulSoup and lxml for more robust parsing
            soup = BeautifulSoup(html_content, 'html.parser')
            tree = etree.HTML(html_content)
            
            if tree is None:
                raise ValueError("Failed to parse HTML")
            
            retail_price = None
            errors = []
            
            # Direct approach based on your working code
            try:
                script = tree.xpath("//script[@id='__NEXT_DATA__']/text()")
                if not script or not script[0].strip():
                    raise ValueError("No __NEXT_DATA__ script found or empty script")
                
                print("Found __NEXT_DATA__ script")
                data = json.loads(script[0])
                
                # Try the direct path from your practice code
                try:
                    retail_price = str(data["props"]["pageProps"]["productDetails"]["salePrice"])
                    print(f"Found price via direct path: {retail_price}")
                except (KeyError, IndexError, TypeError) as e:
                    errors.append(f"Direct path failed: {str(e)}")
                    
                    # Try alternative paths
                    try:
                        props = data.get("props")
                        if not props:
                            raise ValueError("No 'props' in data")
                            
                        page_props = props.get("pageProps")
                        if not page_props:
                            raise ValueError("No 'pageProps' in props")
                            
                        product_details = page_props.get("productDetails")
                        if not product_details:
                            raise ValueError("No 'productDetails' in pageProps")
                            
                        sale_price = product_details.get("salePrice")
                        if sale_price is None:
                            raise ValueError("No 'salePrice' in productDetails")
                            
                        retail_price = str(sale_price)
                        print(f"Found price via alternative JSON path: {retail_price}")
                    except Exception as e:
                        errors.append(f"Alternative JSON path failed: {str(e)}")
            except Exception as e:
                errors.append(f"JSON extraction failed: {str(e)}")
                print(f"JSON extraction error: {str(e)}")
            
            # If JSON extraction failed, try HTML parsing
            if retail_price is None:
                try:
                    # Try direct XPath for price elements
                    price_elements = tree.xpath("//div[contains(@class,'ProductPriceContainer_mrp')][1]")
                    if price_elements and len(price_elements) > 0:
                        price_text = price_elements[0].text_content().strip()
                        price = re.sub(r'[^\d.]', '', price_text)
                        if price:
                            retail_price = price
                            print(f"Found price via XPath: {retail_price}")
                    
                    # If still not found, try CSS selectors with BeautifulSoup
                    if not retail_price:
                        price_elements = soup.select("div[class*='ProductPriceContainer_mrp']")
                        if price_elements:
                            price_text = price_elements[0].get_text(strip=True)
                            price = re.sub(r'[^\d.]', '', price_text)
                            if price:
                                retail_price = price
                                print(f"Found price via CSS selector: {retail_price}")
                
                    # If still not found, try more generic selectors
                    if not retail_price:
                        for selector in [
                            "//span[contains(@class,'Price')]",
                            "//div[contains(@class,'price')]",
                            "//*[contains(text(),'₹')]",
                            "//*[contains(@class,'price') or contains(@class,'Price')]"
                        ]:
                            elements = tree.xpath(selector)
                            if elements and len(elements) > 0:
                                price_text = elements[0].text_content().strip()
                                price = re.sub(r'[^\d.]', '', price_text)
                                if price:
                                    retail_price = price
                                    print(f"Found price via generic selector: {retail_price}")
                                    break
                except Exception as e:
                    errors.append(f"HTML extraction failed: {str(e)}")
                    print(f"HTML extraction error: {str(e)}")
            
            if retail_price is None:
                raise ValueError(f"Could not find retail price on PharmEasy page: {', '.join(errors)}")
                
            try:
                # Ensure price is numeric
                float(retail_price)
            except ValueError:
                raise ValueError(f"Invalid price format: {retail_price}")
                
            return {
                "url": url,
                "price": retail_price,
                "currency": "INR",
                "source": "pharmeasy"
            }
    except httpx.HTTPStatusError as e:
        raise ValueError(f"PharmEasy HTTP error: {e.response.status_code} - {e.response.reason_phrase}")
    except httpx.RequestError as e:
        raise ValueError(f"PharmEasy request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"PharmEasy invalid JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"PharmEasy price fetch error: {str(e)}")
    
async def fetch_truemeds_price(url: str) -> Dict[str, Any]:
    """Fetch the retail price from Truemeds."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/89.0.4389.82 Safari/537.36"
        )
    }
    
    def clean_price(txt):
        if not txt or not isinstance(txt, str):
            return None
        try:
            return float(txt.strip().lstrip("₹").replace(",", ""))
        except ValueError:
            return None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            tree = etree.HTML(response.text)
            if tree is None:
                raise ValueError("Failed to parse HTML")
            
            retail_price = None
            errors = []
            
            # First try to extract from JSON in __NEXT_DATA__
            try:
                script = tree.xpath("//script[@id='__NEXT_DATA__']/text()")
                if not script or not script[0].strip():
                    raise ValueError("No __NEXT_DATA__ script found or empty script")
                    
                data = json.loads(script[0])
                
                props = data.get("props")
                if not props:
                    raise ValueError("No 'props' in data")
                    
                page_props = props.get("pageProps")
                if not page_props:
                    raise ValueError("No 'pageProps' in props")
                    
                current_med = page_props.get("currentMed")
                if not current_med:
                    raise ValueError("No 'currentMed' in pageProps")
                    
                product = current_med.get("product")
                if not product:
                    raise ValueError("No 'product' in currentMed")
                    
                raw_sell = product.get("sellingPrice")
                if raw_sell not in (None, "", 0):
                    retail_price = float(raw_sell)
            except Exception as e:
                # If JSON extraction fails, we'll try HTML next
                errors.append(f"JSON extraction error: {str(e)}")
            
            # Fallback to HTML if JSON extraction failed
            if retail_price is None:
                try:
                    selling_nodes = tree.xpath("//p[contains(@class,'medSelling')]/text()")
                    if selling_nodes and selling_nodes[0].strip():
                        retail_price = clean_price(selling_nodes[0])
                        
                    # If still not found, try alternative selectors
                    if retail_price is None:
                        price_selectors = [
                            "//*[contains(@class,'price')]/text()",
                            "//*[contains(@class,'Price')]/text()",
                            "//span[contains(text(),'₹')]/text()"
                        ]
                        
                        for selector in price_selectors:
                            price_nodes = tree.xpath(selector)
                            if price_nodes:
                                for node in price_nodes:
                                    cleaned = clean_price(node)
                                    if cleaned is not None:
                                        retail_price = cleaned
                                        break
                                if retail_price is not None:
                                    break
                except Exception as e:
                    errors.append(f"HTML extraction error: {str(e)}")
            
            if retail_price is None:
                error_msg = "Could not find retail price in JSON or HTML"
                if errors:
                    error_msg += f": {', '.join(errors)}"
                raise ValueError(error_msg)
            
            return {
                "url": url,
                "price": retail_price,
                "currency": "INR",
                "source": "truemeds"
            }
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Truemeds HTTP error: {e.response.status_code} - {e.response.reason_phrase}")
    except httpx.RequestError as e:
        raise ValueError(f"Truemeds request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Truemeds invalid JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"Truemeds price fetch error: {str(e)}")


@post("/retail_price")
async def get_retail_prices(data: PriceRequest) -> Response:
    """
    Fetch retail prices from multiple sources asynchronously.
    
    Args:
        data: The price request data containing source URLs, pincode, and city.
        
    Returns:
        Response with simplified price format {source: price} or {source: "nan"} for failed fetches.
    """
    tasks = []
    result = {}
    all_sources = ["mrmed", "medkart", "apollo", "netmeds", "pharmeasy", "tata1mg", "truemeds"]
    errors = []
    
    # Initialize all sources with "nan"
    for source in all_sources:
        result[source] = "nan"
    
    # Add tasks for each source if provided
    if data.source.apollo:
        tasks.append(("apollo", fetch_apollo_price(data.source.apollo)))
    
    if data.source.medkart:
        tasks.append(("medkart", fetch_medkart_price(data.source.medkart)))
    
    if data.source.mrmed:
        tasks.append(("mrmed", fetch_mrmed_price(data.source.mrmed)))
    
    if data.source.netmeds:
        tasks.append(("netmeds", fetch_netmeds_price(data.source.netmeds)))
    
    if data.source.pharmeasy:
        tasks.append(("pharmeasy", fetch_pharmeasy_price(data.source.pharmeasy, data.pincode)))
    
    if data.source.tata1mg:
        tasks.append(("tata1mg", fetch_tata1mg_price(data.source.tata1mg, data.city)))
    
    if data.source.truemeds:
        tasks.append(("truemeds", fetch_truemeds_price(data.source.truemeds)))
        
    # Run all tasks concurrently with timeout
    for source_name, task in tasks:
        try:
            price_info = await asyncio.wait_for(task, timeout=45.0)
            # Extract just the price value and ensure it's numeric
            try:
                price_val = price_info["price"]
                # Validate price is numeric
                if isinstance(price_val, (int, float)):
                    result[source_name] = price_val
                else:
                    float(price_val)  # Will raise ValueError if not convertible
                    result[source_name] = price_val
            except (ValueError, TypeError):
                errors.append(f"{source_name}: Invalid price format")
        except asyncio.TimeoutError:
            errors.append(f"{source_name}: Request timed out")
        except Exception as e:
            errors.append(f"{source_name}: {str(e)}")
            # Keep "nan" for failed sources
    
    # Create response object
    response_obj = PriceResponse(
        mrmed={"price": result["mrmed"]} if result["mrmed"] != "nan" else None,
        medkart={"price": result["medkart"]} if result["medkart"] != "nan" else None,
        apollo={"price": result["apollo"]} if result["apollo"] != "nan" else None,
        netmeds={"price": result["netmeds"]} if result["netmeds"] != "nan" else None,
        pharmeasy={"price": result["pharmeasy"]} if result["pharmeasy"] != "nan" else None,
        tata1mg={"price": result["tata1mg"]} if result["tata1mg"] != "nan" else None,
        truemeds={"price": result["truemeds"]} if result["truemeds"] != "nan" else None,
        errors=errors
    )
    
    return Response(
        content=response_obj,
        status_code=200
    )


app = Litestar(
    route_handlers=[get_retail_prices,health_check],
    debug=True
)
