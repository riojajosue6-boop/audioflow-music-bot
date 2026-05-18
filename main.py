import os
import sqlite3
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# CONFIGURACIÓN PRINCIPAL
# Pegamos el token oficial de AudioFlow que nos dio BotFather
TOKEN = "8294251191:AAETFtC3suGk5W9PP4kRVk-_OQuCGTO9CkI"

# CONEXIÓN A BASE DE DATOS (CACHÉ)
def iniciar_db():
    conn = sqlite3.connect('cache_musica.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS canciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            busqueda TEXT UNIQUE,
            file_id TEXT,
            titulo TEXT
        )
    ''')
    conn.commit()
    conn.close()

# FUNCIÓN PARA BUSCAR EN LA RED DE VK
def buscar_en_vk(query):
    """
    Esta función simula una búsqueda web en el catálogo de música pública de VK
    y extrae el enlace directo al archivo .mp3 de forma limpia.
    """
    try:
        # Usamos un user-agent móvil para que VK nos entregue una estructura ligera
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        }
        # Buscamos en la sección de audio libre indexada
        url_busqueda = f"https://m.vk.com/audio?q={requests.utils.quote(query)}"
        respuesta = requests.get(url_busqueda, headers=headers, timeout=10)
        
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.text, 'html.parser')
            
            # Buscamos los contenedores nativos de audio en el HTML de VK
            elementos_audio = soup.find_all('div', class_='audio_item')
            
            if elementos_audio:
                primer_audio = elementos_audio[0]
                # Extraemos el link del MP3 oculto en el atributo de datos de VK
                link_mp3 = primer_audio.get('data-mp3')
                
                # Extraemos el título y artista
                artista = primer_audio.find('span', class_='ai_artist').text.strip() if primer_audio.find('span', class_='ai_artist') else "Artista Desconocido"
                titulo = primer_audio.find('span', class_='ai_title').text.strip() if primer_audio.find('span', class_='ai_title') else "Canción"
                
                if link_mp3:
                    return {
                        "url": link_mp3,
                        "nombre_archivo": f"{artista} - {titulo}"
                    }
    except Exception as e:
        print(f"Error haciendo scraping en VK: {e}")
    return None

# COMANDO /START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje_bienvenida = (
        f"👋 ¡Hola {usuario}! Bienvenido a **AudioFlow** 🌊\n\n"
        "Soy tu bot definitivo para descargar música directo desde la base de datos de VK.\n\n"
        "🎵 **¿Cómo usarme?**\n"
        "Solo escríbeme el nombre de la canción o el artista que quieres escuchar (Ejemplo: `Duki Givenchy`) y yo haré el resto."
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown")

# PROCESADOR DE BÚSQUEDA Y ENTREGA
async def procesar_musica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    busqueda_usuario = update.message.text.strip().lower()
    mensaje_espera = await update.message.reply_text("🔍 Buscando en los servidores de VK, por favor espera...")

    # 1. REVISAR SI YA EXISTE EN NUESTRA CACHÉ
    conn = sqlite3.connect('cache_musica.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM canciones WHERE busqueda = ?", (busqueda_usuario,))
    resultado = cursor.fetchone()

    if resultado:
        # ¡Existe en caché! Telegram reenvía el archivo al instante sin gastar megas
        file_id_guardado = resultado[0]
        await mensaje_espera.edit_text("⚡ ¡Canción encontrada en caché! Enviando de inmediato...")
        await update.message.reply_audio(audio=file_id_guardado)
        conn.close()
        return

    # 2. SI NO ESTÁ EN CACHÉ, BUSCAMOS EN VK
    datos_cancion = buscar_en_vk(busqueda_usuario)
    
    if not datos_cancion:
        await mensaje_espera.edit_text("❌ No encontré esa canción en la base de datos de VK. Intenta escribiendo el nombre de forma diferente.")
        conn.close()
        return

    try:
        await mensaje_espera.edit_text(f"📥 Descargando: {datos_cancion['nombre_archivo']}...")
        
        # Descargamos el archivo temporalmente desde el servidor ruso
        archivo_temp = "temp_audio.mp3"
        audio_bytes = requests.get(datos_cancion['url'], timeout=15).content
        with open(archivo_temp, "wb") as f:
            f.write(audio_bytes)

        await mensaje_espera.edit_text("🚀 Subiendo archivo de audio nativo a Telegram...")
        
        # Enviamos el archivo original al usuario
        with open(archivo_temp, "rb") as f:
            mensaje_audio = await update.message.reply_audio(
                audio=f, 
                title=datos_cancion['nombre_archivo'],
                caption="⚡ Descargado por @audioflow_music_bot\n\n⚠️ Content can be removed at the request of the copyright holder."
            )

        # 3. GUARDAMOS EL FILE_ID EN LA BASE DE DATOS PARA EL PRÓXIMO USUARIO
        file_id_telegram = mensaje_audio.audio.file_id
        try:
            cursor.execute(
                "INSERT INTO canciones (busqueda, file_id, titulo) VALUES (?, ?, ?)",
                (busqueda_usuario, file_id_telegram, datos_cancion['nombre_archivo'])
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass # Por si acaso se hizo una petición doble simultánea

        # Limpiamos el archivo temporal para que Railway no se llene
        if os.path.exists(archivo_temp):
            os.remove(archivo_temp)
            
        await mensaje_espera.delete()

    except Exception as e:
        await mensaje_espera.edit_text("⚠️ Ocurrió un error al procesar el archivo de audio. Intenta de nuevo en unos momentos.")
        print(f"Error de envío: {e}")
        if os.path.exists(archivo_temp):
            os.remove(archivo_temp)
            
    conn.close()

# ARRANQUE DEL BOT
def main():
    iniciar_db()
    # Usamos la API de aplicaciones de python-telegram-bot v20
    application = Application.builder().token(TOKEN).build()

    # Manejadores de comandos y texto
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_musica))

    # El bot se queda escuchando peticiones en Railway
    print("AudioFlow está corriendo en vivo...")
    application.run_polling()

if __name__ == '__main__':
    main()
