import os
import sqlite3
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# CONFIGURACIÓN PRINCIPAL
TOKEN = "8294251191:AAETFtC3suGk5W9PP4kRVk-_OQuCGTO9CkI"

# CONEXIÓN A BASE DE DATOS (SISTEMA DE CACHÉ INTERNO)
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

# MOTOR MEJORADO: INDEXADOR DE AUDIOS COMPLETOS
def buscar_musica_api(query):
    """
    Busca en un indexador global de archivos multimedia de acceso abierto.
    Devuelve pistas 100% completas en formato MP3 sin restricciones de tiempo.
    """
    try:
        query_limpia = requests.utils.quote(query)
        
        # Conexión directa a un buscador de archivos de música libres y completos (Archive Open Data)
        url_api = f"https://archive.org/advancedsearch.php?q={query_limpia}+AND+mediatype:audio&output=json&rows=1"
        respuesta = requests.get(url_api, timeout=12)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            docs = datos.get('response', {}).get('docs', [])
            
            if docs:
                item_id = docs[0].get('identifier')
                titulo = docs[0].get('title', 'Canción Completa')
                
                # Obtenemos los metadatos de los archivos dentro de ese contenedor para sacar el MP3 real
                url_files = f"https://archive.org/metadata/{item_id}"
                res_files = requests.get(url_files, timeout=10).json()
                
                for f in res_files.get('files', []):
                    if f.get('name', '').endswith('.mp3'):
                        # Construimos la URL de descarga directa de la canción completa
                        link_completo = f"https://archive.org/download/{item_id}/{f['name']}"
                        return {
                            "url": link_completo,
                            "nombre_archivo": titulo
                        }
                        
    except Exception as e:
        print(f"Error en motor principal de audio completo: {e}")
        
    # RESPALDO 2: Indexador de música global alternativo directo
    try:
        query_limpia = requests.utils.quote(query)
        url_respaldo = f"https://api.jamendo.com/v3.0/tracks/?client_id=56d30c95&format=json&limit=1&namesearch={query_limpia}"
        res = requests.get(url_respaldo, timeout=10).json()
        if res.get('results'):
            track = res['results'][0]
            if track.get('audio'):
                return {
                    "url": track.get('audio'),
                    "nombre_archivo": f"{track.get('artist_name')} - {track.get('name')}"
                }
    except Exception as e:
        print(f"Error en motor de respaldo: {e}")
        
    return None

# COMANDO /START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje_bienvenida = (
        f"👋 ¡Hola {usuario}! Bienvenido a **AudioFlow** 🌊\n\n"
        "¡Motor de descarga completa activado! Disfruta tus temas de principio a fin.\n\n"
        "🎵 **¿Cómo buscar?**\n"
        "Escríbeme el nombre de la canción o el artista que deseas escuchar."
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown")

# PROCESADOR DE BÚSQUEDA Y ENTREGA (CON CACHÉ ACTIVADA)
async def procesar_musica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    busqueda_usuario = update.message.text.strip().lower()
    
    if not busqueda_usuario or busqueda_usuario.startswith('/'):
        return

    mensaje_espera = await update.message.reply_text("🔍 Buscando canción completa en los servidores, por favor espera...")

    # 1. VERIFICAR SI LA CANCIÓN YA ESTÁ EN LA CACHÉ DE TELEGRAM
    conn = sqlite3.connect('cache_musica.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM canciones WHERE busqueda = ?", (busqueda_usuario,))
    resultado = cursor.fetchone()

    if resultado:
        file_id_guardado = resultado[0]
        await mensaje_espera.edit_text("⚡ ¡Canción encontrada en caché! Enviando de inmediato...")
        await update.message.reply_audio(audio=file_id_guardado)
        conn.close()
        await mensaje_espera.delete()
        return

    # 2. SI NO ESTÁ EN CACHÉ, LE PEDIMOS EL LINK COMPLETO A LA API
    datos_cancion = buscar_musica_api(busqueda_usuario)
    
    if not datos_cancion:
        await mensaje_espera.edit_text("❌ No logré encontrar esa canción completa. Intenta especificando el nombre de otra manera.")
        conn.close()
        return

    archivo_temp = "audioflow_full_track.mp3"
    try:
        await mensaje_espera.edit_text(f"📥 Descargando pista completa:\n🎵 *{datos_cancion['nombre_archivo']}*...", parse_mode="Markdown")
        
        # Descarga del archivo completo de larga duración
        respuesta_audio = requests.get(datos_cancion['url'], timeout=45)
        with open(archivo_temp, "wb") as f:
            f.write(respuesta_audio.content)

        await mensaje_espera.edit_text("🚀 Subiendo canción completa a Telegram...")
        
        # Envío nativo con tu marca y el descargo legal
        with open(archivo_temp, "rb") as f:
            mensaje_audio = await update.message.reply_audio(
                audio=f, 
                title=datos_cancion['nombre_archivo'],
                caption="⚡ Descargado completo por @audioflow_music_bot\n\n⚠️ Content can be removed at the request of the copyright holder."
            )

        # 3. GUARDAR EN CACHÉ PARA EVITAR CONSUMIR RECURSOS EN EL FUTURO
        file_id_telegram = mensaje_audio.audio.file_id
        try:
            cursor.execute(
                "INSERT INTO canciones (busqueda, file_id, titulo) VALUES (?, ?, ?)",
                (busqueda_usuario, file_id_telegram, datos_cancion['nombre_archivo'])
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass 

    except Exception as e:
        await update.message.reply_text("⚠️ Hubo un inconveniente al descargar el archivo completo. Por favor intenta de nuevo.")
        print(f"Error en descarga completa: {e}")
        
    finally:
        if os.path.exists(archivo_temp):
            os.remove(archivo_temp)
        conn.close()
        await mensaje_espera.delete()

# ARRANQUE
def main():
    iniciar_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_musica))

    print("AudioFlow Completo corriendo...")
    application.run_polling()

if __name__ == '__main__':
    main()
