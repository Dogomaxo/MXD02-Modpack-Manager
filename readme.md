# MXD02 Modpack Manager

¡Bienvenido(a) a **MXD02 Modpack Manager**! Esta aplicación facilita la instalación, actualización y gestión de modpacks para Minecraft de forma sencilla y rápida, sin necesidad de manipular manualmente archivos ni carpetas.

---

## Características principales

1. **Instalación/Actualización de Modpacks**  
   - Descarga automática de los archivos necesarios (mods, configuraciones, Forge, etc.) a partir de un **manifest** en la nube.  
   - Aplica “parches” incrementales que añaden o eliminan archivos sin tener que reinstalar todo.

2. **Selección de Memoria RAM**  
   - Desde la interfaz, el usuario puede asignar la cantidad de RAM que el juego utilizará, sin editar manualmente archivos de configuración.

3. **Perfil Personalizado**  
   - El instalador configura automáticamente un perfil en el `launcher_profiles.json` de Minecraft, guardando la carpeta de mods, la versión de Forge, y los argumentos de Java.

4. **Modo Oscuro**  
   - Presenta una interfaz oscura y moderna, diseñada para minimizar la fatiga visual.

5. **Compatibilidad**  
   - Soporta Windows 10/11 (y, en teoría, Windows 7/8 con Python y librerías adecuadas).  
   - Detecta e instala los archivos en la carpeta `.minecraft` por defecto o la que el usuario elija.

6. **Abrir Minecraft**  
   - Incluye un botón para abrir el launcher de Minecraft. Intentará encontrar la ruta del launcher oficial o permitir que el usuario seleccione manualmente.

---

## Requisitos

- **Python 3.7+** (para desarrollo).  
- En **Windows**, si usas la versión “.exe” compilada, no necesitas Python instalado.  
- **Conexión a internet** para descargar el manifest y los archivos del modpack.

Para la descompresión de ciertos formatos (`.rar`, `.7z`), puede que se requiera `patool` y herramientas externas instaladas en el sistema operativo (p. ej., 7-Zip).

---

## Descarga e Instalación

1. Ve a la sección de [Releases](./releases) de este repositorio.  
2. Descarga el **`.exe`** correspondiente a la última versión (o el `.zip` si se usa modo onedir).  
3. Descomprime (si es `.zip`) y sitúa la carpeta donde prefieras.  
4. Ejecuta `MXD02 Modpack Manager.exe`.  
   - Si Windows te advierte sobre un fichero desconocido, revisa la [sección de seguridad](#seguridad-y-falsos-positivos).  
   - Opcionalmente, puedes “Crear acceso directo” al `.exe`.

---

## Uso de la Aplicación

1. **Manifest URL**: introduce la URL del *manifest* (un archivo JSON que contiene la versión del modpack, la URL de descarga, el hash, etc.).  
2. **.mxd02modpack**: carpeta en donde se guardarán archivos internos del modpack. Suele ubicarse en `%APPDATA%/.mxd02modpack`.  
3. **.minecraft/versions**: ruta a la carpeta `versions` de tu Minecraft, generalmente `%APPDATA%/.minecraft/versions`.  
4. **.minecraft dir**: la carpeta base de tu Minecraft (por defecto `%APPDATA%/.minecraft`).  
5. **Memoria RAM (GB)**: selecciona cuánta RAM quieres asignar a Minecraft.  
6. Pulsa **Instalar / Actualizar**. El programa descargará y aplicará el pack o parche necesario.  
7. Pulsa **ABRIR MINECRAFT** (opcional) para iniciar el launcher de Minecraft con el perfil recién creado/actualizado.

---

## Parches y Actualizaciones

- Si existe una versión “Full” (completa) disponible, se instalará primero.  
- Luego, si el *manifest* indica que hay un parche (por ejemplo, para eliminar un mod o actualizar archivos específicos), el programa lo descargará y aplicará.  
- La aplicación guarda la versión instalada en `installed_version.txt` dentro de `.mxd02modpack` para saber si es necesario volver a actualizar.

---

## Seguridad y Falsos Positivos

Algunos antivirus o Windows Defender pueden marcar los ejecutables creados con PyInstaller como “sospechosos” o “maliciosos”. Esto es un **falso positivo** habitual en aplicaciones empaquetadas.  
- **Solución**:  
  - Asegúrate de descargar el `.exe` desde fuentes confiables (este repositorio).  
  - Si tu antivirus lo bloquea, añade una excepción o reputa el archivo como seguro.  
  - Revisa la documentación sobre [Code Signing](https://learn.microsoft.com/en-us/windows/win32/seccrypto/code-signing) y falsos positivos en PyInstaller si tienes dudas.

---

## Ejecución en Entorno de Desarrollo (Opcional)

Si prefieres trabajar con el código fuente:

1. Clona o descarga este repositorio. 
 
2. Instala dependencias (por ejemplo):
   ```bash
   pip install -r requirements.txt

3. Ejecuta:
   ```bash
   python mxd02_modpackinstaller.py

4. (Opcional) Compila con PyInstaller:
   ```bash
   pyinstaller --onefile --windowed mxd02_modpackinstaller.py

---

## Preguntas Frecuentes (FAQ)

1. **Me sale un error de “pyunpack” o “requests” no encontrado.**
   - Asegúrate de que el .exe incluya esas librerías (modo onedir/onefile con PyInstaller) o de haber instalado dichas dependencias en tu entorno si ejecutas el script en Python.

2. **El parche no se aplica aunque haya una versión nueva.**
   - Asegúrate de que el número de versión del parche sea mayor que el de la versión completa instalada. Por ejemplo, si la versión “full” es `0.31`, el parche debe ser `0.31.1` o `0.32`, nunca `0.4` (porque la comparación de `0.4` vs. `0.31` puede entenderse como una versión menor, dependiendo de tu lógica de comparación de versiones).
   - Verifica también que el manifest contenga la sección `"patch"` con la información correcta (URL, filename, hash, etc.).

3. **El instalador dice que no puede descomprimir el .zip/.rar.**
   - Si tu modpack está en formato `.rar` o `.7z`, asegúrate de tener instaladas las dependencias adecuadas (por ejemplo, `patool` y 7-Zip/unrar) en tu sistema.  
   - Si estás ejecutando el `.exe` empaquetado, verifica que `pyunpack` y `patool` se hayan incluido correctamente al compilar.

4. **¿Puedo instalar varios modpacks diferentes con este mismo instalador?**
   - Este instalador está enfocado en un único “manifest” (un modpack principal). Sin embargo, podrías modificar el manifest de manera que apunte a diferentes paquetes o `full` packs y usarlo para gestionar varias “builds” de Minecraft.  
   - Ten en cuenta que cada modpack podría requerir su propia carpeta `.mxd02modpack` y su perfil en `launcher_profiles.json`.

5. **¿Dónde se almacenan los archivos que se descargan?**
   - Por defecto, el instalador crea una carpeta `\_temp_down_` dentro de `.mxd02modpack` para las descargas temporales, y `\_temp_full_` o `\_temp_patch_` para la extracción.  
   - Al final de la instalación, esos directorios temporales se eliminan, dejando solo los archivos finales en `.mxd02modpack`.

6. **¿Cómo puedo desinstalar el modpack?**
   - Basta con cerrar Minecraft y, si lo deseas, borrar la carpeta .mxd02modpack, además de eliminar el perfil del launcher en launcher_profiles.json. Sin embargo, hazlo con precaución si quieres conservar tus partidas (mundos).

7. **¿Cómo contribuyo o propongo mejoras?**
   - Haz un *fork* de este repositorio y crea un *pull request* con tus cambios. O bien, abre un *Issue* explicando tu propuesta de mejora, corrección de bugs o nuevas funciones.

---

## Créditos y Licencia

- Proyecto creado por [Dogomaxo].  
- Iconos e imágenes pertenecen a [Bunnadexu].  
- Este proyecto no está afiliado ni respaldado oficialmente por Mojang o Microsoft.

Este proyecto está licenciado bajo la **Licencia MIT**. Consulta el archivo `LICENSE` para más detalles.

### Atribuciones

El proyecto utiliza las siguientes dependencias externas:

- [PyQt5](https://pypi.org/project/PyQt5/) - Licencia GPL v3.0
- [Requests](https://pypi.org/project/requests/) - Licencia Apache 2.0
- [pyunpack](https://pypi.org/project/pyunpack/) - Licencia GPL v3.0
- [patool](https://pypi.org/project/patool/) - Licencia GPL v3.0

Consulta el archivo `NOTICE` para más información sobre estas dependencias y sus respectivas licencias.

**¡Gracias por usar MXD02 Modpack Manager!**  
Para cualquier duda o comentario, abre un _Issue_ en el repositorio o contáctame por [https://github.com/Dogomaxo].

---

### Changelog (Historial de Cambios)

#### **v1.0**
- Primera versión pública con instalación y parche básico.

#### **v1.1**
- 🔄 **Corrección:** Flujo de actualizaciones y parches mejorado.
- 🐞 **Corrección:** Solucionado un bug que descargaba todo nuevamente aun teniendo el último parche instalado.
- ➕ **Función añadida:** Ahora el archivo `manifest.json` puede modificar la carpeta `libraries` de `.minecraft` para realizar una instalación correcta de Forge y evitar el error `1` en Minecraft Launcher. (Créditos a _Bunnadexu_ por detectar el error).
- ➕ **Función añadida:** Soporte para borrar carpetas/directorios mediante el archivo `manifest.json`.

#### **v1.2**
- 🔄 **Corrección:** Flujo de actualizaciones en parches mejorado.
- 🐞 **Corrección:** Solucionado un bug que no permitía descargar mas de un parche, por ende, reestructuración de la forma de organizar parches en el archivo `manifest.json`.
- 🐞 **Corrección:** Solucionado un bug que descargaba la versión base a pesar de tener una versión superior a esta.
- ➕ **Función añadida:** Soporte para añadir archivos a la carpeta raíz del modpack creando una carpeta llamada 'additional_files' dentro del zip.

---

_Dedicado para mis Mejores amigos._
