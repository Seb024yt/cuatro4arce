import sys
import time
import os
import shutil
import glob
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
try:
    from webdriver_manager.core.os_manager import ChromeType
except ImportError:
    from webdriver_manager.core.utils import ChromeType

from .data_processor import consolidate_data
from .email_sender import send_email

MONTH_MAP = {
    "enero": ("01", "Enero"),
    "febrero": ("02", "Febrero"),
    "marzo": ("03", "Marzo"),
    "abril": ("04", "Abril"),
    "mayo": ("05", "Mayo"),
    "junio": ("06", "Junio"),
    "julio": ("07", "Julio"),
    "agosto": ("08", "Agosto"),
    "septiembre": ("09", "Septiembre"),
    "octubre": ("10", "Octubre"),
    "noviembre": ("11", "Noviembre"),
    "diciembre": ("12", "Diciembre")
}

MONTH_ORDER = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def run_sii_process(job_id, data, update_status_func):
    """
    Orchestrates the SII process: Login -> Loop Months -> Download -> Consolidate
    """
    automator = None
    
    try:
        update_status_func("Iniciando proceso...", "running")
        
        # Create base directories
        base_dir = os.path.join(os.getcwd(), "sii_data")
        update_status_func(f"Directorio base: {base_dir}", "running")

        descargados_dir = os.path.join(base_dir, "descargados")
        output_dir = os.path.join(base_dir, "generados")
        
        os.makedirs(descargados_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Job specific download dir
        download_dir = os.path.join(descargados_dir, job_id)
        os.makedirs(download_dir, exist_ok=True)
        update_status_func("Carpetas creadas correctamente", "running")

        update_status_func("Configurando navegador...", "running")
        automator = SIIAutomator(download_dir)
        
        # 1. Login
        update_status_func("Iniciando sesión en SII...")
        if not automator.login(data.rutEmpresa, data.claveSII):
            update_status_func("Error: Credenciales inválidas o fallo en login", "failed")
            return

        # 2. Iterate Months
        target_month_idx = MONTH_ORDER.index(data.mes.lower())
        months_to_process = MONTH_ORDER[:target_month_idx + 1]
        
        for m_name in months_to_process:
            m_code, m_display = MONTH_MAP[m_name]
            update_status_func(f"Descargando datos de {m_display} {data.anio}...")
            
            # Download RCV
            if not automator.get_rcv(m_code, data.anio):
                print(f"Warning: Could not get RCV for {m_name}")
                
            # Download Honorarios
            if not automator.get_honorarios(m_display, data.anio):
                print(f"Warning: Could not get Honorarios for {m_name}")
                
            # Sleep slightly to avoid rate limiting
            time.sleep(1)

        # 3. Consolidate
        update_status_func("Consolidando información y generando Excel...")
        output_file = os.path.join(output_dir, f"Planilla_{job_id}.xlsx")
        
        consolidate_data(download_dir, output_file)
        
        # 4. Finish
        update_status_func("Finalizado. Preparando descarga...", "completed")
        
        # Email sending logic - DISABLED per user request
        # if data.correo:
        #     subject = f"Planilla de Impuestos Generada - {data.rutEmpresa}"
        #     body = f"""Hola,
        # 
        # Adjunto encontrarás la planilla de impuestos generada para la empresa {data.rutEmpresa} correspondiente al periodo {data.mes} {data.anio}.
        # 
        # Saludos,
        # Tu Sistema de Impuestos
        # """
        #     success, msg = send_email(data.correo, subject, body, output_file)
        #     if success:
        #         print(f"Email sent to {data.correo}")
        #     else:
        #         print(f"Failed to send email: {msg}")
        
    except Exception as e:
        print(f"Process Error: {e}")
        update_status_func(f"Error inesperado: {str(e)}", "failed")
    finally:
        if automator:
            automator.close()
        # Keep downloads as requested by user
        # if os.path.exists(download_dir):
        #    try:
        #        shutil.rmtree(download_dir)
        #    except:
        #        pass

class SIIAutomator:
    def __init__(self, download_dir=None):
        print("DEBUG: Initializing SIIConnector...")
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--headless=new")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        # options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--remote-debugging-pipe")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--single-process")
        options.add_argument("--no-zygote")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Add temporary user data dir to avoid conflicts
        import tempfile
        user_data_dir = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={user_data_dir}")

        # Detect binary
        binary_path = self._get_chrome_binary()
        is_chromium = False
        if binary_path:
            print(f"Using Chrome binary at: {binary_path}")
            options.binary_location = binary_path
            if "chromium" in binary_path.lower():
                is_chromium = True
        else:
            print("Warning: No Chrome/Chromium binary found in standard locations.")
        
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            if is_chromium:
                manager = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM)
            else:
                manager = ChromeDriverManager()
            
            service = Service(manager.install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(60) # 60 seconds timeout
            self.wait = WebDriverWait(self.driver, 30)
            
            # Enable downloads in headless mode via CDP
            try:
                self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                    'behavior': 'allow',
                    'downloadPath': self.download_dir
                })
                print(f"CDP Download behavior set to: {self.download_dir}")
            except Exception as e:
                print(f"Warning: Failed to set CDP download behavior: {e}")

            print("WebDriver initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize WebDriver: {e}")
            raise e

    def _get_chrome_binary(self):
        """Attempts to find the Chrome or Chromium binary."""
        # Check env var first
        if os.environ.get("CHROME_BIN"):
            return os.environ.get("CHROME_BIN")
            
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
            "/usr/bin/chrome",
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        # Check shutil.which
        for name in ["google-chrome", "chromium", "chromium-browser", "chrome"]:
            path = shutil.which(name)
            if path:
                return path
        return None

    def login(self, rut, clave):
        self.rut = rut  # Store RUT for later use
        try:
            print(f"Logging in with RUT: {rut}")
            url = "https://zeusr.sii.cl//AUT2000/InicioAutenticacion/IngresoRutClave.html?https://misiir.sii.cl/cgi_misii/siihome.cgi"
            print(f"Navigating to {url}...")
            self.driver.get(url)
            print("Page loaded. Looking for input fields...")
            
            rut_input = self.wait.until(EC.presence_of_element_located((By.ID, "rutcntr")))
            print("RUT input found.")
            rut_input.clear()
            rut_input.send_keys(rut)
            
            clave_input = self.driver.find_element(By.ID, "clave")
            clave_input.clear()
            clave_input.send_keys(clave)
            
            # Submit
            print("Submitting form...")
            sys.stdout.flush()
            
            # Retry loop for clicking 'Ingresar'
            login_success = False
            for attempt in range(3):
                try:
                    print(f"Login attempt {attempt + 1}...")
                    try:
                        ingresar_btn = self.driver.find_element(By.ID, "bt_ingresar")
                        ingresar_btn.click()
                        print("Clicked 'Ingresar' button.")
                    except:
                        print("Button not found or not clickable, using ENTER key on password field...")
                        clave_input.send_keys(Keys.RETURN)
                    
                    sys.stdout.flush()
                    
                    # Wait and check if URL changed
                    time.sleep(5)
                    current_url = self.driver.current_url
                    print(f"Current URL: {current_url}")
                    
                    if "IngresoRutClave" not in current_url:
                        login_success = True
                        break
                    else:
                        print("Still on login page...")
                        # Check for error alerts
                        try:
                            alert = self.driver.switch_to.alert
                            print(f"Alert found: {alert.text}")
                            alert.accept()
                        except:
                            pass
                        
                        # Check for error text in body
                        body_text = self.driver.find_element(By.TAG_NAME, "body").text
                        if "Error" in body_text or "inválida" in body_text:
                            print(f"Login error detected in page text.")
                            
                except Exception as e:
                    print(f"Error during login attempt {attempt + 1}: {e}")
                    sys.stdout.flush()
                
                time.sleep(2)

            print("Woke up from login attempts. Checking final URL...")
            current_url = self.driver.current_url
            print(f"Final URL after login: {current_url}")

            # Write debug info to file
            try:
                with open(os.path.join(self.download_dir, "debug_info.txt"), "w", encoding="utf-8") as f:
                    f.write(f"URL: {current_url}\n")
                    f.write(f"Title: {self.driver.title}\n")
                    f.write("-" * 20 + "\n")
                    f.write(self.driver.find_element(By.TAG_NAME, "body").text)
            except Exception as e:
                print(f"Failed to write debug info: {e}")

            # Take debug screenshot
            try:
                screenshot_path = os.path.join(self.download_dir, "debug_login_attempt.png")
                self.driver.save_screenshot(screenshot_path)
                print(f"Screenshot saved to {screenshot_path}")
            except Exception as e:
                print(f"Failed to save screenshot: {e}")
            
            if "IngresoRutClave" in current_url:
                print("Still on login page. Login might have failed.")
                # Try to read error message
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    print(f"Page text content preview: {body_text[:200]}")
                except:
                    pass
                return False
            
            # Check for "Actualizar datos" modal
            try:
                mas_tarde_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'ACTUALIZAR MÁS TARDE')]")
                for btn in mas_tarde_btns:
                    if btn.is_displayed():
                        print("Dismissing 'Update Data' modal...")
                        btn.click()
                        time.sleep(2)
            except Exception as e:
                print(f"Error checking modal: {e}")

            print("Login seems successful.")
            return True
            
        except Exception as e:
            print(f"Login Error: {e}")
            try:
                with open(os.path.join(self.download_dir, "error_log.txt"), "w") as f:
                    f.write(str(e))
            except:
                pass
            try:
                self.driver.save_screenshot(os.path.join(self.download_dir, "login_error.png"))
                print("Saved login_error.png")
            except:
                pass
            return False

    def _download_detalles(self, context_name):
        print(f"Attempting to download details for {context_name}...")
        files_before = set(glob.glob(os.path.join(self.download_dir, "*")))
        
        # 1. Try clicking button
        try:
            # Try specific text for context if needed, but usually "Descargar Detalles" is common
            btns = self.driver.find_elements(By.TAG_NAME, "button")
            target_btn = None
            for b in btns:
                if "Descargar Detalles" in b.text:
                    target_btn = b
                    break
            
            if target_btn:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", target_btn)
                time.sleep(1)
                try:
                    target_btn.click()
                except:
                    self.driver.execute_script("arguments[0].click();", target_btn)
                print(f"Clicked 'Descargar Detalles' button for {context_name}.")
            else:
                print(f"Button 'Descargar Detalles' not found for {context_name}.")
        except Exception as e:
            print(f"Error clicking download button ({context_name}): {e}")

        # 2. Check Modals
        time.sleep(2)
        try:
            modal_btns = self.driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceptar') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continuar') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'si, descargar')]")
            for mb in modal_btns:
                if mb.is_displayed():
                    print(f"Found modal button: {mb.text}. Clicking...")
                    try:
                        mb.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", mb)
                    time.sleep(1)
        except Exception as e_modal:
            print(f"Error checking modals: {e_modal}")

        # 3. Wait and Check
        download_success = False
        for _ in range(15):
            files_now = set(glob.glob(os.path.join(self.download_dir, "*")))
            new_files = files_now - files_before
            valid_new = [f for f in new_files if not f.endswith('.crdownload') and (f.endswith('.csv') or f.endswith('.txt'))] 
            
            if valid_new:
                print(f"File downloaded successfully ({context_name}): {valid_new}")
                download_success = True
                break
            time.sleep(1)

        # 4. Fallback Angular
        if not download_success:
            print(f"No file downloaded via button for {context_name}. Attempting Angular trigger...")
            try:
                script_dl = """
                var el = document.querySelector('[ng-controller="ComunCtrl"]');
                if(el) {
                    var s = angular.element(el).scope();
                    if(s) { 
                        s.descargaDetalle(); 
                        s.$apply();
                        return "Called"; 
                    }
                }
                return "NotFound";
                """
                res = self.driver.execute_script(script_dl)
                print(f"Direct Angular call result: {res}")
                
                for _ in range(15):
                    files_now = set(glob.glob(os.path.join(self.download_dir, "*")))
                    new_files = files_now - files_before
                    valid_new = [f for f in new_files if not f.endswith('.crdownload') and (f.endswith('.csv') or f.endswith('.txt'))]
                    
                    if valid_new:
                        print(f"File downloaded via Angular trigger ({context_name}): {valid_new}")
                        download_success = True
                        break
                    time.sleep(1)
            except Exception as e_dl:
                print(f"Direct Angular call failed ({context_name}): {e_dl}")

        if not download_success:
            print(f"CRITICAL: Failed to download file for {context_name}.")
            self.driver.save_screenshot(os.path.join(self.download_dir, f"debug_download_fail_{context_name}.png"))
        
        return download_success

    def get_rcv(self, month, year):
        # month should be '01', '02', etc.
        try:
            # Go to RCV main page
            print("Navigating to RCV main page...")
            self.driver.get("https://www4.sii.cl/consdcvinternetui/")
            
            # Wait for the period selectors
            print("Waiting for period selectors...")
            sys.stdout.flush()
            
            # Angular automation to bypass UI issues
            angular_success = False
            try:
                print(f"Executing Angular script to submit form for {self.rut} {month}/{year}...")
                script = f"""
                try {{
                    var element = document.querySelector("div[ng-controller='IndexCtrl']");
                    if (!element) return "Element not found";
                    var scope = angular.element(element).scope();
                    if (!scope) return "Scope not found";
                    scope.$apply(function() {{
                        scope.rut = '{self.rut}';
                        scope.periodoMes = '{month}';
                        scope.periodoAnho = '{year}';
                        scope.consultarFiltro(scope.rut, scope.periodoMes, scope.periodoAnho);
                    }});
                    return "Success";
                }} catch (e) {{
                    return "Error: " + e.message;
                }}
                """
                result = self.driver.execute_script(script)
                print(f"Angular script result: {result}")
                if result == "Success":
                    angular_success = True
                time.sleep(3) # Wait for digest and network
            except Exception as e:
                print(f"Angular script execution failed: {e}")
                sys.stdout.flush()

            if not angular_success:
                print("Angular script failed or returned error. Falling back to manual interaction...")
                # Fallback to manual interaction
                try:
                    # Select RUT
                    rut_select = self.driver.find_element(By.NAME, "rut")
                    # Use send_keys for selection which is more robust
                    rut_select.send_keys(self.rut)
                    print(f"Selected RUT {self.rut} via send_keys")
                    
                    # Select Month
                    period_mes = self.driver.find_element(By.ID, "periodoMes")
                    # Find display name for month code
                    mes_display = month
                    for m_key, (m_code, m_disp) in MONTH_MAP.items():
                        if m_code == month:
                            mes_display = m_disp
                            break
                    
                    period_mes.send_keys(mes_display)
                    print(f"Selected Month {mes_display} via send_keys")
                    
                    # Select Year
                    period_anio = self.driver.find_element(By.XPATH, "//select[@ng-model='periodoAnho']")
                    period_anio.send_keys(str(year))
                    print(f"Selected Year {year} via send_keys")
                    
                    # Click Consultar
                    btn_consultar = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Consultar')]")
                    self.driver.execute_script("arguments[0].click();", btn_consultar)
                    print("Manual fallback clicked 'Consultar' via JS click")
                    
                    # Also try standard click
                    try:
                        btn_consultar.click()
                        print("Manual fallback clicked 'Consultar' via standard click")
                    except:
                        pass
                        
                except Exception as ex:
                    print(f"Manual fallback failed: {ex}")

            # Wait for results to load
            print("Waiting for results...")
            time.sleep(10)
            
            # Save debug screenshot after Consultar
            self.driver.save_screenshot(os.path.join(self.download_dir, "after_consultar.png"))

            # Wait for results
            print("Waiting for results/download button...")
            sys.stdout.flush()
            time.sleep(5)

            # Debug screenshot
            try:
                self.driver.save_screenshot(os.path.join(self.download_dir, "rcv_results.png"))
                with open(os.path.join(self.download_dir, "rcv_results_debug.txt"), "w", encoding="utf-8") as f:
                    f.write(self.driver.find_element(By.TAG_NAME, "body").text)
            except:
                pass
            
            # 6. Click "Descargar Detalles" (Compras)
            self._download_detalles("Compras")

            # Check for downloaded files
            print(f"Checking downloads in {self.download_dir}...")
            files = glob.glob(os.path.join(self.download_dir, "*"))
            print(f"Files found: {files}")

            # Switch to Ventas
            print("Switching to Ventas...")
            try:
                self.driver.execute_script("document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());")
            except:
                pass

            try:
                # Try JS click first to avoid interception
                tab_venta = self.driver.find_element(By.CSS_SELECTOR, 'a[ui-sref="venta"]')
                self.driver.execute_script("arguments[0].click();", tab_venta)
            except:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, 'a[ui-sref="venta"]').click()
                except Exception as e:
                    print(f"Error clicking Venta: {e}")
                
            time.sleep(2)
            
            # Download Ventas
            if not self._download_detalles("Ventas"):
                print("Failed to download Ventas details.")
                
            return True
        except Exception as e:
            print(f"Error getting RCV: {e}")
            return False

    def get_honorarios(self, month_name, year):
        # month_name: "Enero", "Febrero", etc.
        try:
            print(f"Downloading Honorarios for {month_name} {year}")
            self.driver.get("https://loa.sii.cl/cgi_IMT/TMBCOC_MenuConsultasContribRec.cgi")
            
            # Select Year
            # Note: VBA sets year in sheet but URL/Form might rely on current year or input
            # The VBA only selects Month in 'cbmesinformemensual'. Year might be implicit or in another field.
            # Assuming year selection if available, otherwise just month.
            
            select_mes = self.wait.until(EC.presence_of_element_located((By.NAME, "cbmesinformemensual")))
            select_mes.send_keys(month_name)
            
            self.driver.find_element(By.ID, "cmdconsultar1").click()
            time.sleep(2)
            
            # Download
            try:
                dl_btn = self.driver.find_element(By.XPATH, "//input[@value='Ver informe como planilla electrónica']")
                dl_btn.click()
                time.sleep(3)
            except:
                print("No Honorarios download button found")
                
            return True
        except Exception as e:
            print(f"Error getting Honorarios: {e}")
            return False

    def close(self):
        self.driver.quit()
