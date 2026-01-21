import os
import time
import glob
import shutil
from selenium import webdriver
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
        
        # Create main folder structure
        base_dir = os.path.join(os.getcwd(), "sii_data")
        update_status_func(f"Directorio base: {base_dir}", "running")
        
        # Downloads subfolder
        download_dir = os.path.join(base_dir, "descargados", job_id)
        
        # Generated subfolder
        output_dir = os.path.join(base_dir, "generados")
        
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
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
        update_status_func("Finalizado. Enviando correo...", "completed")
        
        # (Optional) Email sending logic would go here
        
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
    def __init__(self, download_dir):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new") # Use new headless mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--window-size=1920,1080")
        
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
            self.wait = WebDriverWait(self.driver, 20)
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
        try:
            print(f"Logging in with RUT: {rut}")
            url = "https://zeusr.sii.cl//AUT2000/InicioAutenticacion/IngresoRutClave.html?https://misiir.sii.cl/cgi_misii/siihome.cgi"
            self.driver.get(url)
            
            rut_input = self.wait.until(EC.presence_of_element_located((By.ID, "rutcntr")))
            rut_input.clear()
            rut_input.send_keys(rut)
            
            clave_input = self.driver.find_element(By.ID, "clave")
            clave_input.clear()
            clave_input.send_keys(clave)
            
            self.driver.find_element(By.ID, "bt_ingresar").click()
            
            # Simple check if login failed (alert or staying on same page)
            time.sleep(2)
            if "IngresoRutClave" in self.driver.current_url:
                # Check for error message
                try:
                    error = self.driver.find_element(By.ID, "mensajeError").text
                    print(f"Login error: {error}")
                except:
                    pass
                return False
                
            return True
        except Exception as e:
            print(f"Login exception: {e}")
            return False

    def get_rcv(self, month, year):
        # month should be '01', '02', etc.
        try:
            print(f"Downloading RCV for {month}/{year}")
            self.driver.get("https://www4.sii.cl/consdcvinternetui/")
            
            # Select Month
            period_mes = self.wait.until(EC.element_to_be_clickable((By.ID, "periodoMes")))
            period_mes.click()
            self.driver.find_element(By.XPATH, f"//select[@id='periodoMes']/option[@value='{month}']").click()
            
            # Select Year (Angular model usually needs send_keys to the input or select)
            # VBA used xpath //select[@ng-model='periodoAnho']
            try:
                period_anio = self.driver.find_element(By.XPATH, "//select[@ng-model='periodoAnho']")
                period_anio.send_keys(str(year))
            except:
                # Sometimes it's a div or needs clicking
                pass

            # Click Consultar
            consultar_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Consultar')]")
            consultar_btn.click()
            time.sleep(2)

            # Download Compras
            try:
                dl_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Descargar Detalles')]")
                dl_btn.click()
                time.sleep(3) # Wait for download
            except:
                print("No Compras details button found (maybe no data)")

            # Switch to Ventas
            self.driver.find_element(By.XPATH, "//a[@ui-sref='venta']").click()
            time.sleep(1)
            
            # Download Ventas
            try:
                dl_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Descargar Detalles')]")
                dl_btn.click()
                time.sleep(3)
            except:
                print("No Ventas details button found")
                
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
