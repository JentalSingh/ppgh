# usp_pdf_fetcher_actual_pdf.py
"""
USP PDF URL FETCHER - USES ACTUAL PDF FILE
Uploads the actual PDF from your system
"""

import os
import time
import logging
import random
import re
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from faker import Faker
from twocaptcha import TwoCaptcha

load_dotenv()

# ============================================================
# LOGGING SETUP
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("usp_pdf_fetcher")

# ============================================================
# CONFIGURATION
# ============================================================
TARGET_URL = "https://ppgh.fflch.usp.br/en/form_qualificacao"
VERIFIED_SITEKEY = "6Lc1u6ApAAAAAAFWutGlCbhF04XXCf885VcobStf"
TWO_CAPTCHA_API_KEY = os.getenv("TWO_CAPTCHA_API_KEY")

# ✅ PDF FILE PATH - ACTUAL PDF FROM YOUR SYSTEM
PDF_FILE_PATH = "SWA232.pdf"  # Aapke system mein jo PDF hai

fake = Faker()

# ============================================================
# CAPTCHA FUNCTIONS
# ============================================================
def solve_recaptcha_2captcha(sitekey, pageurl):
    if not TWO_CAPTCHA_API_KEY:
        logger.error("❌ No 2Captcha API key found!")
        return None
    
    try:
        solver = TwoCaptcha(TWO_CAPTCHA_API_KEY)
        result = solver.recaptcha(
            sitekey=sitekey,
            url=pageurl
        )
        if result and isinstance(result, dict):
            token = result.get('code')
            logger.info(f"✅ Captcha solved: {token[:30]}...")
            return token
        return None
    except Exception as e:
        logger.error(f"❌ 2Captcha error: {e}")
        return None

def auto_detect_sitekey(page):
    try:
        sitekey = page.evaluate("""
            () => {
                let element = document.querySelector('[data-sitekey]');
                if (element) return element.getAttribute('data-sitekey');
                return null;
            }
        """)
        return sitekey or VERIFIED_SITEKEY
    except:
        return VERIFIED_SITEKEY

def inject_captcha_token(page, token):
    page.evaluate(f"""
        (token) => {{
            document.querySelectorAll('textarea[name="g-recaptcha-response"]').forEach(textarea => {{
                textarea.value = token;
                textarea.dispatchEvent(new Event('input', {{bubbles: true}}));
                textarea.dispatchEvent(new Event('change', {{bubbles: true}}));
            }});
        }}
    """, token)
    time.sleep(2)

# ============================================================
# PDF FUNCTIONS - ✅ ACTUAL PDF USE KAREGA
# ============================================================
def find_pdf_file():
    """
    Find PDF file to upload
    Priority: 1. SWA232.pdf, 2. Any .pdf file in directory
    """
    # Check if SWA232.pdf exists
    if os.path.exists("SWA232.pdf"):
        logger.info(f"✅ Found PDF: SWA232.pdf")
        return os.path.abspath("SWA232.pdf")
    
    # Check for any PDF in current directory
    pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
    if pdf_files:
        logger.info(f"✅ Found PDF: {pdf_files[0]}")
        return os.path.abspath(pdf_files[0])
    
    # Check Downloads folder
    downloads_path = os.path.expanduser("~/Downloads")
    pdf_files = [f for f in os.listdir(downloads_path) if f.endswith('.pdf')]
    if pdf_files:
        pdf_path = os.path.join(downloads_path, pdf_files[0])
        logger.info(f"✅ Found PDF in Downloads: {pdf_files[0]}")
        return pdf_path
    
    logger.error("❌ No PDF file found!")
    return None

def upload_pdf_files_automated(page, pdf_path):
    """Upload actual PDF file to the form"""
    logger.info(f"📎 Uploading PDF: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"❌ PDF file not found: {pdf_path}")
        return False
    
    # Find file inputs
    file_inputs = page.query_selector_all('input[type="file"]')
    
    if not file_inputs:
        page.evaluate("""
            () => {
                document.querySelectorAll('input[type="file"]').forEach(el => {
                    el.style.display = 'block';
                });
            }
        """)
        time.sleep(1)
        file_inputs = page.query_selector_all('input[type="file"]')
    
    uploaded_count = 0
    for i, file_input in enumerate(file_inputs):
        try:
            file_input.set_input_files(pdf_path)
            logger.info(f"✅ Uploaded PDF to file input #{i+1}")
            uploaded_count += 1
            time.sleep(1)
        except Exception as e:
            logger.debug(f"Could not upload to file input #{i+1}: {e}")
    
    if uploaded_count == 0:
        # Try specific selectors
        specific_selectors = [
            'input[name="files[sugestao_de_banca]"]',
            'input[name="files[relatorio]"]',
            '#edit-sugestao-de-banca-upload',
            '#edit-relatorio-upload'
        ]
        
        for selector in specific_selectors:
            try:
                el = page.locator(selector).first
                if el and el.is_visible(timeout=1000):
                    el.set_input_files(pdf_path)
                    logger.info(f"✅ Uploaded PDF to: {selector}")
                    uploaded_count += 1
                    time.sleep(1)
            except:
                pass
    
    if uploaded_count > 0:
        logger.info(f"✅ Successfully uploaded {uploaded_count} PDF file(s)")
        return True
    else:
        logger.error("❌ Failed to upload PDF files!")
        return False

# ============================================================
# FORM FUNCTIONS
# ============================================================
def generate_form_data():
    return {
        "usp_number": str(random.randint(1000000, 9999999)),
        "course": "Geography",
        "full_name": fake.name(),
        "email": fake.email(),
        "advisor": fake.name(),
        "title": fake.sentence(nb_words=6),
        "pages": str(random.randint(50, 150)),
        "infrastructure": "Sim",
        "multimedia": "Não",
        "video_conference": "Não"
    }

def fill_form_fields(page, form_data):
    logger.info("📝 Filling form fields...")
    
    fields = {
        'input[name="numero_usp"]': form_data['usp_number'],
        'input[name="nome_completo"]': form_data['full_name'],
        'input[name="e_mail"]': form_data['email'],
        'input[name="orientador"]': form_data['advisor'],
        'input[name="titulo_do_trabalho"]': form_data['title'],
        'input[name="numero_de_paginas"]': form_data['pages']
    }
    
    for selector, value in fields.items():
        try:
            el = page.locator(selector).first
            if el and el.is_visible(timeout=2000):
                el.click()
                time.sleep(0.3)
                el.fill(value)
                logger.info(f"✅ Filled: {selector}")
        except Exception as e:
            logger.debug(f"Could not fill {selector}: {e}")
    
    try:
        el = page.locator('select[name="curso"]').first
        if el and el.is_visible(timeout=2000):
            el.select_option(label=form_data['course'])
            logger.info(f"✅ Selected course: {form_data['course']}")
    except:
        pass
    
    radio_values = [
        form_data['infrastructure'],
        form_data['multimedia'],
        form_data['video_conference']
    ]
    
    for value in radio_values:
        try:
            radio = page.locator(f'input[type="radio"][value="{value}"]').first
            if radio and radio.is_visible(timeout=1000):
                radio.click()
                logger.info(f"✅ Selected radio: {value}")
        except:
            pass

def submit_form_automated(page):
    logger.info("🚀 Submitting form...")
    
    submit_selectors = [
        'input[type="submit"][value="Submit"]',
        'input.webform-button--submit',
        'input#edit-submit',
        'button[type="submit"]'
    ]
    
    for selector in submit_selectors:
        try:
            el = page.locator(selector).first
            if el and el.is_visible(timeout=2000):
                el.click()
                logger.info(f"✅ Clicked: {selector}")
                return True
        except:
            continue
    
    try:
        page.evaluate("""
            () => {
                let buttons = document.querySelectorAll('input[type="submit"]');
                for (let btn of buttons) {
                    if (btn.value && (btn.value.toLowerCase().includes('submit') || btn.value.toLowerCase().includes('enviar'))) {
                        btn.click();
                        return;
                    }
                }
                document.querySelector('input#edit-submit')?.click();
            }
        """)
        logger.info("✅ Submitted via JavaScript fallback")
        return True
    except:
        logger.error("❌ Could not submit form!")
        return False

# ============================================================
# NETWORK CAPTURE - PDF URL FETCH
# ============================================================
def fetch_pdf_url():
    """Main function - uses actual PDF file"""
    
    chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = os.path.expanduser("~") + "\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"
    
    # ✅ Find actual PDF file
    pdf_path = find_pdf_file()
    if not pdf_path:
        logger.error("❌ No PDF file found to upload!")
        logger.info("💡 Make sure SWA232.pdf is in the current directory")
        return None
    
    logger.info(f"📄 Using PDF: {pdf_path}")
    
    form_data = generate_form_data()
    logger.info(f"👤 Name: {form_data['full_name']}")
    logger.info("🤖 Starting automated submission...")
    
    with sync_playwright() as p:
        # Clean profile
        profile_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "USP_PDF_Profile")
        if os.path.exists(profile_dir):
            try:
                shutil.rmtree(profile_dir)
                logger.info("✅ Profile cleaned")
            except:
                pass
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            executable_path=chrome_path,
            headless=False,
            viewport={'width': 1366, 'height': 768},
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = context.new_page()
        
        # Store captured PDF URLs
        captured_pdf_urls = []
        
        # Setup network monitoring
        def handle_response(response):
            try:
                url = response.url
                if '.pdf' in url.lower():
                    captured_pdf_urls.append(url)
                    logger.info(f"🌐 Network capture - PDF found: {url}")
                    
                    # Check if it's the actual PDF (not inline-files)
                    if 'inline-files' not in url and 'sites' in url:
                        logger.info(f"🎯 Real PDF URL captured: {url}")
            except:
                pass
        
        page.on("response", handle_response)
        
        try:
            # ===== STEP 1: Navigate =====
            logger.info("🌐 Navigating to form...")
            page.goto(TARGET_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            
            # ===== STEP 2: Solve Captcha =====
            sitekey = auto_detect_sitekey(page)
            logger.info(f"🔑 Sitekey: {sitekey[:20]}...")
            
            token = solve_recaptcha_2captcha(sitekey, TARGET_URL)
            if not token:
                logger.error("❌ Captcha failed!")
                context.close()
                return None
            
            inject_captcha_token(page, token)
            time.sleep(2)
            
            # ===== STEP 3: Fill Form =====
            fill_form_fields(page, form_data)
            
            # ===== STEP 4: Upload Actual PDF =====
            if not upload_pdf_files_automated(page, pdf_path):
                logger.error("❌ PDF upload failed!")
                context.close()
                return None
            
            time.sleep(2)
            
            # ===== STEP 5: Submit Form =====
            if not submit_form_automated(page):
                logger.error("❌ Form submission failed!")
                context.close()
                return None
            
            # ===== STEP 6: Wait for Response =====
            logger.info("⏳ Waiting for submission response...")
            time.sleep(10)
            
            # ===== STEP 7: Extract PDF URL from network =====
            logger.info("🔍 Searching for PDF URL...")
            
            # Check captured URLs
            real_pdf_urls = []
            for url in captured_pdf_urls:
                if 'inline-files' not in url and 'sites' in url:
                    real_pdf_urls.append(url)
                    logger.info(f"✅ Real PDF URL: {url}")
            
            if real_pdf_urls:
                pdf_url = real_pdf_urls[0]
                logger.info(f"🎉 PDF URL found: {pdf_url}")
                
                # Save to file
                with open("usp_pdf_url.txt", "w") as f:
                    f.write(f"PDF URL: {pdf_url}\n")
                    f.write(f"Name: {form_data['full_name']}\n")
                    f.write(f"PDF File: {os.path.basename(pdf_path)}\n")
                    f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                print("\n" + "="*70)
                print("📄 PDF URL FOUND")
                print("="*70)
                print(f"👤 Name: {form_data['full_name']}")
                print(f"📄 Uploaded PDF: {os.path.basename(pdf_path)}")
                print(f"🔗 PDF URL: {pdf_url}")
                print("="*70 + "\n")
                
                context.close()
                return pdf_url
            
            # ===== STEP 8: Fallback - Check page source =====
            logger.info("🔍 Fallback: Searching page source...")
            html_content = page.content()
            pdf_matches = re.findall(r'https?://[^\s"\'<>]+\.pdf', html_content)
            
            real_pdf_matches = [url for url in pdf_matches if 'inline-files' not in url]
            
            if real_pdf_matches:
                pdf_url = real_pdf_matches[0]
                logger.info(f"🎉 PDF URL found in page source: {pdf_url}")
                
                with open("usp_pdf_url.txt", "w") as f:
                    f.write(f"PDF URL: {pdf_url}\n")
                    f.write(f"Name: {form_data['full_name']}\n")
                    f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                context.close()
                return pdf_url
            
            logger.warning("⚠️ No PDF URL found!")
            context.close()
            return None
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            context.close()
            return None

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("📄 USP PDF FETCHER - ACTUAL PDF UPLOAD")
    print("="*70)
    print("✅ Uploads actual PDF file (SWA232.pdf)")
    print("✅ Captures real PDF URL from network")
    print("="*70 + "\n")
    
    if not TWO_CAPTCHA_API_KEY:
        print("❌ No 2Captcha API key found in .env file!")
        print("💡 Add to .env: TWO_CAPTCHA_API_KEY=your_key_here")
        exit(1)
    
    # Check if PDF exists
    if not os.path.exists("SWA232.pdf"):
        print("⚠️ SWA232.pdf not found in current directory!")
        print("💡 Make sure the PDF file is in the same folder")
        pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
        if pdf_files:
            print(f"📄 Found these PDFs: {pdf_files}")
        else:
            print("❌ No PDF files found!")
            exit(1)
    
    result = fetch_pdf_url()
    
    if result:
        print(f"\n🎉 SUCCESS! PDF URL: {result}")
    else:
        print("\n❌ Failed to fetch PDF URL.")