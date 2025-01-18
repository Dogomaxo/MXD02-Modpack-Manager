import subprocess
import sys
import os
import json
import shutil
import requests
import hashlib
from datetime import datetime

from pyunpack import Archive  # Para extraer .zip/.rar/.7z
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QTextEdit, QVBoxLayout,
    QWidget, QHBoxLayout, QLineEdit, QFileDialog, QProgressBar, QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPalette, QColor, QIcon

# ---------------------------------------------------------
# CONFIGURACIONES
# ---------------------------------------------------------

if hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

icon_path = os.path.join(base_path, "resources", "icon.ico")

# (Cambia aquí la URL raw de tu Pastebin con el manifest)
DEFAULT_MANIFEST_URL = "https://pastebin.com/raw/mPKas0Ci"

# Rutas "universales" en Windows (usando APPDATA)
DEFAULT_MINECRAFT_DIR = os.path.join(os.getenv("APPDATA"), ".minecraft")
DEFAULT_MODPACK_DIR   = os.path.join(os.getenv("APPDATA"), ".mxd02modpack")
FORGE_VERSIONS_DIR    = os.path.join(DEFAULT_MINECRAFT_DIR, "versions")

INSTALLED_VERSION_FILE = "installed_version.txt"  # Dentro de .mxd02modpack
MAX_DOWNLOAD_RETRIES   = 5  # Reintentos de descarga
HASH_ALGORITHM         = "sha256"  # para la verificación del ZIP

# Archivo local para guardar la configuración de la GUI (ej. memoria RAM)
SETTINGS_FILE = "user_settings.json"


# ---------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------

def set_dark_theme(app):

    app.setStyle("Fusion")
    """
    Aplica un tema oscuro usando QPalette.
    """
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))         # Fondo de ventanas
    palette.setColor(QPalette.WindowText, Qt.white)               # Texto de ventanas
    palette.setColor(QPalette.Base, QColor(42, 42, 42))           # Fondo de widgets como QLineEdit
    palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))  
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)                     # Texto en widgets (LineEdit, etc.)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))         # Fondo de botones
    palette.setColor(QPalette.ButtonText, Qt.white)               # Texto de botones
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))    # Color de selección
    palette.setColor(QPalette.HighlightedText, Qt.black)          # Texto seleccionado

    app.setPalette(palette)

    style_sheet = """
        QWidget {
            font-family: "Segoe UI";
            font-size: 9pt;
            color: #ffffff;
            background-color: #353535;
        }
        QLineEdit {
            background-color: #2A2A2A;
            border: 1px solid #666666;
            padding: 4px;
        }
        QTextEdit {
            background-color: #2A2A2A;
            border: 1px solid #666666;
        }
        QComboBox {
            background-color: #2A2A2A;
            border: 1px solid #666666;
        }
        QPushButton {
            background-color: #3C3C3C;
            border: 1px solid #555555;
            padding: 5px 10px;
        }
        QPushButton:hover {
            background-color: #4C4C4C;
        }
        QProgressBar {
            background-color: #2A2A2A;
            border: 1px solid #666666;
            text-align: center;
            color: #ffffff;
        }
        QProgressBar::chunk {
            background-color: #2a82da; /* color de la barra */
        }
    """
    app.setStyleSheet(style_sheet)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def calc_file_hash(file_path, hash_type="sha256"):
    """Calcula el hash del archivo (SHA-256 por defecto)."""
    h = hashlib.new(hash_type)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            h.update(chunk)
    return h.hexdigest()

def copy_all(src, dst, log_func=None):
    """
    Copia recursivamente el contenido de 'src' dentro de 'dst', 
    sobrescribiendo archivos existentes.
    """
    ensure_dir(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if log_func:
            log_func(f"Copiando de {s} a {d}")
        if os.path.isdir(s):
            copy_all(s, d, log_func)
        else:
            shutil.copy2(s, d)

def add_or_update_profile(launcher_profiles_path, profile_id, profile_data, logger=None):
    """
    Agrega o actualiza el perfil con 'profile_id' en 'launcher_profiles.json'
    sin sobrescribir otros perfiles. Además, conserva campos personalizados 
    si el perfil ya existe.
    """
    if logger:
        logger(f"Modificando el archivo launcher_profiles.json en: {launcher_profiles_path}")

    if not os.path.isfile(launcher_profiles_path):
        data = {"profiles": {}}
    else:
        try:
            with open(launcher_profiles_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {"profiles": {}}

    if "profiles" not in data:
        data["profiles"] = {}

    old_profile = data["profiles"].get(profile_id, {})
    # Mezclamos los datos antiguos con los nuevos:
    # (lo básico aquí es sobreescribir lo que necesitamos,
    #  y dejar lo que el usuario haya configurado)
    for key, value in profile_data.items():
        old_profile[key] = value

    data["profiles"][profile_id] = old_profile

    with open(launcher_profiles_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

    if logger:
        logger(f"Perfil '{profile_id}' agregado/actualizado en launcher_profiles.json.")

def load_user_settings():
    """
    Carga la configuración guardada en SETTINGS_FILE (si existe).
    Devuelve un dict con 'ram' y cualquier otra configuración que quieras guardar.
    """
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"ram": "4"}  # Valor por defecto (4 GB)

def save_user_settings(settings):
    """
    Guarda la configuración en SETTINGS_FILE.
    """
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4)

# ---------------------------------------------------------
# HILO DE ACTUALIZACIÓN
# ---------------------------------------------------------
class UpdateWorker(QThread):
    """
    Hilo que realiza la actualización con "Full" o "Patch" según el manifest.
    """
    logSignal = pyqtSignal(str)      
    progressSignal = pyqtSignal(int)
    finishedSignal = pyqtSignal(bool, str)

    def __init__(self, manifest_url, modpack_dir, forge_versions_dir, minecraft_dir, user_ram, parent=None):
        super().__init__(parent)
        self.manifest_url       = manifest_url
        self.modpack_dir        = modpack_dir
        self.forge_versions_dir = forge_versions_dir
        self.minecraft_dir      = minecraft_dir
        self.user_ram           = user_ram  # e.g. "4" o "6" (GB)
        self.cancelled          = False

    def run(self):
        try:
            # 1. Descargar manifest
            self.log("Descargando manifest...")
            manifest_data = self.download_json(self.manifest_url)
            if not manifest_data:
                raise Exception("No se pudo obtener el manifest o está vacío.")

            latest_version = manifest_data.get("latestVersion")
            full_info = manifest_data.get("full", {})

            if not latest_version or "version" not in full_info:
                raise Exception("El manifest no contiene la sección 'full' adecuada o 'latestVersion'.")

            # 2. Leer versión instalada (si existe)
            installed_version_path = os.path.join(self.modpack_dir, INSTALLED_VERSION_FILE)
            current_version = None
            if os.path.isfile(installed_version_path):
                with open(installed_version_path, 'r', encoding='utf-8') as f:
                    current_version = f.read().strip()

            self.log(f"Versión instalada: {current_version if current_version else 'Ninguna'}")
            self.log(f"Última versión disponible: {latest_version}")

            # 3. Si ya está en la última versión => mostrar mensaje y salir
            if current_version == latest_version:
                self.log("Ya tienes la última versión instalada. No es necesario actualizar.")
                self.finishedSignal.emit(False, f"{latest_version} (ya instalado)")
                return

            # 4. Instalar Full Pack si la versión instalada no coincide con el Full más reciente
            if not current_version or self.is_version_greater(full_info["version"], current_version):
                self.log(f"Instalando Full Pack {full_info['version']}...")
                self.install_full(full_info)
                current_version = full_info["version"]

            # 5. Aplicar parches solo si se requiere
            patches = {key: value for key, value in manifest_data.items() if key.startswith("patch")}
            for patch_key, patch_info in sorted(patches.items()):
                patch_version = patch_info.get("version")
                if self.is_version_greater(patch_version, current_version):
                    self.log(f"Aplicando {patch_key} para actualizar a la versión {patch_version}...")
                    self.install_patch(patch_info)
                    current_version = patch_version

            # 6. Finalización
            self.finishedSignal.emit(False, latest_version)

        except Exception as e:
            self.log(f"ERROR: {e}")
            self.finishedSignal.emit(True, str(e))

    def is_version_greater(self, v1, v2):
        """
        Compara strings de versión muy simple (p.e. "0.31.1" > "0.31").
        Puedes reemplazarlo con un parser más robusto si quieres.
        """
        def parse_version(v):
            return list(map(int, v.split(".")))
        return parse_version(v1) > parse_version(v2)

    def download_json(self, url):
        """Descarga y parsea JSON con reintentos."""
        for attempt in range(MAX_DOWNLOAD_RETRIES):
            if self.cancelled:
                return None
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                self.log(f"Fallo al descargar manifest (intento {attempt+1}/{MAX_DOWNLOAD_RETRIES}): {e}")
        return None

    def install_full(self, full_info):
        """Descarga e instala la versión Full."""
        version       = full_info["version"]
        url           = full_info["url"]
        filename      = full_info["filename"]
        expected_hash = full_info.get("hash")  # sha-256

        self.log(f"Instalando Full Pack {version}...")

        # 1. Descargar el ZIP (con reintentos)
        archive_path = self.download_file_with_retries(url, filename, expected_hash)
        if not archive_path:
            raise Exception("No se pudo descargar o verificar el Full Pack.")

        # 2. Descomprimir en carpeta temporal
        temp_dir = os.path.join(self.modpack_dir, "_temp_full_")
        ensure_dir(temp_dir)
        self.log("Descomprimiendo Full Pack...")
        self.extract_archive(archive_path, temp_dir)

        # 3. Copiar la carpeta .mxd02modpack
        src_modpack = os.path.join(temp_dir, ".mxd02modpack")
        if os.path.isdir(src_modpack):
            self.log("Copiando .mxd02modpack...")
            copy_all(src_modpack, self.modpack_dir, self.log)

        # 4. Copiar forgeVersion a .minecraft/versions (si existe)
        forge_version_dir = os.path.join(temp_dir, "forgeVersion")
        if os.path.isdir(forge_version_dir):
            self.log("Copiando forgeVersion en .minecraft/versions...")
            for item in os.listdir(forge_version_dir):
                s = os.path.join(forge_version_dir, item)
                d = os.path.join(self.forge_versions_dir, item)
                if os.path.isdir(s):
                    copy_all(s, d, self.log)
                else:
                    shutil.copy2(s, d)

        # 5. Copiar libraries a .minecraft directory (si existe)
        libraries_dir = os.path.join(temp_dir, "libraries")
        if os.path.isdir(libraries_dir):
            self.log("Copiando libraries en .minecraft...")
            for item in os.listdir(libraries_dir):
                s = os.path.join(libraries_dir, item)
                d = os.path.join(self.minecraft_dir, "libraries", item)
                if os.path.isdir(s):
                    copy_all(s, d, self.log)
                else:
                    shutil.copy2(s, d)

        # 6. Copiar el contenido de "additional_files" si existe
        additional_dir = os.path.join(temp_dir, "additional_files")
        if os.path.isdir(additional_dir):
            self.log("Se encontró la carpeta 'additional_files'. Copiando su contenido a .mxd02modpack...")
            copy_all(additional_dir, self.modpack_dir)
        else:
            self.log("No se encontró la carpeta 'additional_files' en el Full Pack.")

        # 7. Guardar la versión instalada en installed_version.txt
        installed_version_path = os.path.join(self.modpack_dir, INSTALLED_VERSION_FILE)
        with open(installed_version_path, 'w', encoding='utf-8') as f:
            f.write(version)

        # 8. (Opcional) Agregar/actualizar perfil en launcher_profiles.json
        launcher_profiles_path = os.path.join(self.minecraft_dir, "launcher_profiles.json")
        # Crea un ID único para el perfil
        profile_id = "23fc205a599a1340b3cb7ee096b9760d"
        # Prepara el JSON del perfil
        profile_data = {
            "created": "2024-12-30T05:01:57.789Z",
            "gameDir": self.modpack_dir,
            "icon": "Furnace_On",
            "javaArgs": f"-Xmx{self.user_ram}G -XX:+UnlockExperimentalVMOptions -XX:+UseG1GC -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=32M",
            "lastUsed": datetime.utcnow().isoformat() + "Z",
            "lastVersionId": "1.19.2-forge-43.4.0",
            "name": "mxd02modpack",
            "type": "custom"
        }
        add_or_update_profile(launcher_profiles_path, profile_id, profile_data, logger=self.log)

        # Limpieza final
        shutil.rmtree(temp_dir, ignore_errors=True)
        os.remove(archive_path)

        self.log(f"Instalación Full Pack {version} completada.")

    def install_patch(self, patch_info):
        """
        Descarga un ZIP que contiene solo los archivos modificados. 
        Simplemente se descomprime y se copian/reescriben los archivos en .mxd02modpack 
        (y/o la carpeta de forgeVersion, si aplica).
        """
        version       = patch_info["version"]
        url           = patch_info["url"]
        filename      = patch_info["filename"]
        expected_hash = patch_info.get("hash")

        self.log(f"Instalando Parche {version}...")

        archive_path = self.download_file_with_retries(url, filename, expected_hash)
        if not archive_path:
            raise Exception("No se pudo descargar o verificar el Parche.")

        temp_dir = os.path.join(self.modpack_dir, "_temp_patch_")
        ensure_dir(temp_dir)
        self.log("Descomprimiendo Parche...")
        self.extract_archive(archive_path, temp_dir)

        files_to_remove = patch_info.get("filesToRemove", [])
        for rel_path in files_to_remove:
            # Suponiendo que rel_path es relativo a .mxd02modpack
            target_path = os.path.join(self.modpack_dir, rel_path)
            if os.path.exists(target_path):
                self.log(f"Eliminando archivo obsoleto: {target_path}")
                os.remove(target_path)

        dir_to_remove = patch_info.get("dirToRemove", [])
        for rel_path in dir_to_remove:
            # Suponiendo que rel_path es relativo a .mxd02modpack
            target_path = os.path.join(self.modpack_dir, rel_path)
            if os.path.exists(target_path):
                self.log(f"Eliminando carpeta obsoleta: {target_path}")
                try:
                    os.chmod(target_path, 0o777)  # Cambiar permisos
                    shutil.rmtree(target_path)
                except Exception as e:
                    self.log(f"ERROR al eliminar la carpeta: {e}")

        # En el parche, podrías tener la misma estructura:
        #   .mxd02modpack/
        #   forgeVersion/
        #   resourcepacks/
        #   additional_files/
        #   u otras carpetas
        # Copia igual que en full, pero sólo lo que exista
        src_modpack = os.path.join(temp_dir, ".mxd02modpack")
        if os.path.isdir(src_modpack):
            self.log("Copiando parche .mxd02modpack...")
            copy_all(src_modpack, self.modpack_dir, self.log)

        forge_version_dir = os.path.join(temp_dir, "forgeVersion")
        if os.path.isdir(forge_version_dir):
            self.log("Copiando parche forgeVersion en .minecraft/versions...")
            for item in os.listdir(forge_version_dir):
                s = os.path.join(forge_version_dir, item)
                d = os.path.join(self.forge_versions_dir, item)
                if os.path.isdir(s):
                    copy_all(s, d, self.log)
                else:
                    shutil.copy2(s, d)

        #Copiar el contenido de "additional_files" si existe
        additional_dir = os.path.join(temp_dir, "additional_files")
        if os.path.isdir(additional_dir):
            self.log("Se encontró la carpeta 'additional_files'. Copiando su contenido a .mxd02modpack...")
            copy_all(additional_dir, self.modpack_dir)
        else:
            self.log("No se encontró la carpeta 'additional_files' en el Parche.")

        libraries_dir = os.path.join(temp_dir, "libraries")
        if os.path.isdir(libraries_dir):
            self.log("Copiando parche libraries en .minecraft...")
            for item in os.listdir(libraries_dir):
                s = os.path.join(libraries_dir, item)
                d = os.path.join(self.minecraft_dir, "libraries", item)
                if os.path.isdir(s):
                    copy_all(s, d, self.log)
                else:
                    shutil.copy2(s, d)

        # Actualizamos la versión instalada (esto depende de tu criterio)
        installed_version_path = os.path.join(self.modpack_dir, INSTALLED_VERSION_FILE)
        with open(installed_version_path, 'w', encoding='utf-8') as f:
            f.write(version)

        # También actualizamos el perfil con la RAM que el usuario eligió:
        launcher_profiles_path = os.path.join(self.minecraft_dir, "launcher_profiles.json")
        profile_id = "23fc205a599a1340b3cb7ee096b9760d"
        profile_data = {
            # Solo actualizamos lastUsed y javaArgs si quieres
            "lastUsed": datetime.utcnow().isoformat() + "Z",
            "javaArgs": f"-Xmx{self.user_ram}G -XX:+UnlockExperimentalVMOptions -XX:+UseG1GC -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=32M",
        }
        add_or_update_profile(launcher_profiles_path, profile_id, profile_data, logger=self.log)

        shutil.rmtree(temp_dir, ignore_errors=True)
        os.remove(archive_path)

        self.log(f"Parche {version} instalado con éxito.")

    def download_file_with_retries(self, url, filename, expected_hash=None):
        """
        Descarga un archivo con reintentos, verifica el hash si se proporciona.
        Retorna la ruta local al archivo o None si falla.
        """
        temp_download_dir = os.path.join(self.modpack_dir, "_temp_down_")
        ensure_dir(temp_download_dir)
        dest_path = os.path.join(temp_download_dir, filename)

        for attempt in range(MAX_DOWNLOAD_RETRIES):
            if self.cancelled:
                return None
            try:
                self.log(f"Descargando {filename} (intento {attempt+1}/{MAX_DOWNLOAD_RETRIES})...")
                self.progressSignal.emit(0)
                self._download(url, dest_path)
                if expected_hash:
                    file_hash = calc_file_hash(dest_path, HASH_ALGORITHM)
                    if file_hash.lower() != expected_hash.lower():
                        raise Exception(f"Hash distinto. Esperado={expected_hash}, obtenido={file_hash}")
                return dest_path
            except Exception as e:
                self.log(f"Error en descarga {filename}: {e}")
        return None

    def _download(self, url, dest_path):
        """Descarga con `requests`, actualizando barra de progreso."""
        resp = requests.get(url, stream=True, timeout=15)
        resp.raise_for_status()
        total = int(resp.headers.get('content-length', 0))
        downloaded = 0

        with open(dest_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if self.cancelled:
                    return
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        prog = int(downloaded * 100 / total)
                        self.progressSignal.emit(prog)

    def extract_archive(self, archive_path, extract_to):
        self.progressSignal.emit(0)
        try:
            Archive(archive_path).extractall(extract_to)
            self.log(f"Archivo extraído correctamente: {archive_path}")
        except Exception as e:
            self.log(f"ERROR al descomprimir el archivo: {e}")
            raise
        self.progressSignal.emit(100)

    def log(self, message):
        self.logSignal.emit(message)

    def cancel(self):
        self.cancelled = True

import os

def try_open_known_paths():
    possible_paths = [
        r"C:\Program Files (x86)\Minecraft Launcher\MinecraftLauncher.exe",
        r"C:\Program Files\Minecraft Launcher\MinecraftLauncher.exe",
        r"C:\Program Files (x86)\Minecraft\MinecraftLauncher.exe",
        r"C:\Program Files\Minecraft\MinecraftLauncher.exe",
    ]
    for path in possible_paths:
        if os.path.isfile(path):
            os.startfile(path)
            return True
    return False

def open_minecraft_store_edition():
    # Ajusta la siguiente línea con el PackageFamilyName y AppID correctos
    launcher_uri = r"shell:AppsFolder\Microsoft.4297127D64EC6_8wekyb3d8bbwe!Minecraft"
    subprocess.run(["explorer.exe", launcher_uri], check=False)

# ---------------------------------------------------------
# INTERFAZ GRÁFICA CON PYQT5
# ---------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MXD02 Modpack Manager v1.2 Release")
        self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(300, 80, 800, 600)

        # Layout principal
        layout = QVBoxLayout()

        # Cargamos ajustes del usuario (RAM, etc.)
        self.user_settings = load_user_settings()

        # 1) Campo de texto para la URL del manifest
        row_manifest = QHBoxLayout()
        row_manifest.addWidget(QLabel("Manifest URL:"))
        self.manifestEdit = QLineEdit(DEFAULT_MANIFEST_URL)
        row_manifest.addWidget(self.manifestEdit)
        layout.addLayout(row_manifest)

        # 2) Campo para .mxd02modpack
        row_modpack = QHBoxLayout()
        row_modpack.addWidget(QLabel(".mxd02modpack:"))
        self.modpackPathEdit = QLineEdit(DEFAULT_MODPACK_DIR)
        self.modpackBrowseBtn = QPushButton("Examinar")
        self.modpackBrowseBtn.clicked.connect(self.browse_modpack_dir)
        row_modpack.addWidget(self.modpackPathEdit)
        row_modpack.addWidget(self.modpackBrowseBtn)
        layout.addLayout(row_modpack)

        # 3) Campo para la carpeta .minecraft/versions
        row_forge = QHBoxLayout()
        row_forge.addWidget(QLabel(".minecraft/versions:"))
        self.forgePathEdit = QLineEdit(FORGE_VERSIONS_DIR)
        self.forgeBrowseBtn = QPushButton("Examinar")
        self.forgeBrowseBtn.clicked.connect(self.browse_forge_dir)
        row_forge.addWidget(self.forgePathEdit)
        row_forge.addWidget(self.forgeBrowseBtn)
        layout.addLayout(row_forge)

        # 4) Campo para la carpeta base de .minecraft (opcional, por si se requiere)
        row_minecraft = QHBoxLayout()
        row_minecraft.addWidget(QLabel(".minecraft dir:"))
        self.minecraftPathEdit = QLineEdit(DEFAULT_MINECRAFT_DIR)
        self.minecraftBrowseBtn = QPushButton("Examinar")
        self.minecraftBrowseBtn.clicked.connect(self.browse_minecraft_dir)
        row_minecraft.addWidget(self.minecraftPathEdit)
        row_minecraft.addWidget(self.minecraftBrowseBtn)
        layout.addLayout(row_minecraft)

        # 5) Selección de Memoria RAM
        row_ram = QHBoxLayout()
        row_ram.addWidget(QLabel("Memoria RAM (GB):"))
        self.ramCombo = QComboBox()
        ram_options = ["2", "3", "4", "6", "8", "12", "16", "24", "32"]
        self.ramCombo.addItems(ram_options)
        if self.user_settings["ram"] in ram_options:
            self.ramCombo.setCurrentText(self.user_settings["ram"])
        else:
            self.ramCombo.setCurrentText("4")
        row_ram.addWidget(self.ramCombo)
        layout.addLayout(row_ram)

        # ---- Área de texto para logs
        self.logArea = QTextEdit()
        self.logArea.setReadOnly(True)
        layout.addWidget(self.logArea)

        # ---- Barra de progreso
        self.progressBar = QProgressBar()
        layout.addWidget(self.progressBar)

        # ---- Fila de botones: Instalar/Actualizar y Abrir Minecraft
        row_buttons = QHBoxLayout()
        self.installBtn = QPushButton("INSTALAR / ACTUALIZAR")
        self.installBtn.clicked.connect(self.on_install_clicked)
        row_buttons.addWidget(self.installBtn)

        self.openMCBtn = QPushButton("ABRIR MINECRAFT")
        self.openMCBtn.clicked.connect(self.on_open_minecraft)
        row_buttons.addWidget(self.openMCBtn)
        layout.addLayout(row_buttons)

        # ---- Botón Cancelar
        self.cancelBtn = QPushButton("CANCELAR")
        self.cancelBtn.clicked.connect(self.on_cancel_clicked)
        self.cancelBtn.setEnabled(False)
        layout.addWidget(self.cancelBtn)

        # ---- Contenedor principal
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.workerThread = None

        # Al final del init, chequeamos si hay actualizaciones
        self.check_for_updates_on_start()

    def check_for_updates_on_start(self):
        """
        Verifica si hay una versión o parche más nuevo que el actual.
        De manera sencilla y sin hilos: descarga el manifest, lee la versión instalada,
        y compara. Si hay algo más nuevo, muestra un mensaje.
        """
        try:
            manifest_url = self.manifestEdit.text().strip()
            if not manifest_url:
                return  # Si no hay URL, no hacemos nada
            r = requests.get(manifest_url, timeout=10)
            r.raise_for_status()
            data = r.json()
            latest_version = data.get("latestVersion")
            full_info = data.get("full", {})
            patch_info = data.get("patch", {})

            # Leemos versión instalada
            installed_version_path = os.path.join(self.modpackPathEdit.text(), INSTALLED_VERSION_FILE)
            current_version = None
            if os.path.isfile(installed_version_path):
                with open(installed_version_path, 'r', encoding='utf-8') as f:
                    current_version = f.read().strip()

            if not current_version:
                # No hay nada instalado => no decimos nada especial
                return

            # Comparar con "latestVersion"
            if current_version != latest_version:
                QMessageBox.information(
                    self,
                    "Nueva versión disponible",
                    f"Hay una nueva versión Full disponible: {latest_version}\n"
                    "Puedes hacer clic en INSTALAR/ACTUALIZAR."
                )
                return

            # Si current_version == latest_version, checkear si el parche es mayor
            patch_version = patch_info.get("version")
            if patch_version and self.is_version_greater(patch_version, latest_version):
                QMessageBox.information(
                    self,
                    "Parche disponible",
                    f"Se encontró un parche: v{patch_version}\n"
                    "Puedes hacer clic en INSTALAR/ACTUALIZAR para aplicarlo."
                )

        except Exception as e:
            # Silenciar o mostrar en log, depende de ti
            self.logArea.append(f"No se pudo verificar actualizaciones: {e}")

    def is_version_greater(self, v1, v2):
        def parse_version(v):
            return list(map(int, v.split(".")))
        return parse_version(v1) > parse_version(v2)

    def browse_modpack_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta .mxd02modpack", self.modpackPathEdit.text())
        if path:
            self.modpackPathEdit.setText(path)

    def browse_forge_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta versions", self.forgePathEdit.text())
        if path:
            self.forgePathEdit.setText(path)

    def browse_minecraft_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta .minecraft", self.minecraftPathEdit.text())
        if path:
            self.minecraftPathEdit.setText(path)

    def on_install_clicked(self):
        manifest_url = self.manifestEdit.text().strip()
        modpack_dir  = self.modpackPathEdit.text().strip()
        forge_dir    = self.forgePathEdit.text().strip()
        minecraft_dir = self.minecraftPathEdit.text().strip()

        if not manifest_url:
            QMessageBox.warning(self, "Error", "Debes especificar la URL del manifest.")
            return

        # Guardamos la configuración del usuario (RAM)
        self.user_settings["ram"] = self.ramCombo.currentText()
        save_user_settings(self.user_settings)

        self.logArea.clear()
        self.installBtn.setEnabled(False)
        self.cancelBtn.setEnabled(True)
        self.progressBar.setValue(0)

        # Crear hilo
        self.workerThread = UpdateWorker(manifest_url, modpack_dir, forge_dir, minecraft_dir, user_ram=self.user_settings["ram"])
        self.workerThread.logSignal.connect(self.append_log)
        self.workerThread.progressSignal.connect(self.update_progress)
        self.workerThread.finishedSignal.connect(self.on_finished)
        self.workerThread.start()

    def on_open_minecraft(self):
        # 1) Primero intentamos abrir rutas comunes
        if try_open_known_paths():
            return
        open_minecraft_store_edition()

    def on_cancel_clicked(self):
        if self.workerThread:
            self.workerThread.cancel()
            self.append_log("Cancelando operación...")

    def update_progress(self, value):
        self.progressBar.setValue(value)

    def on_finished(self, error_occurred, info):
        self.installBtn.setEnabled(True)
        self.cancelBtn.setEnabled(False)
        if error_occurred:
            QMessageBox.critical(self, "Error", f"Se produjo un error:\n{info}")
        else:
            QMessageBox.information(self, "Completado", f"Proceso finalizado. Versión instalada: {info}")

    def append_log(self, text):
        self.logArea.append(text)
        print(text)  # opcional para la consola

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    # Aplicamos el tema oscuro
    set_dark_theme(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()