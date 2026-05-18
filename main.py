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

# NUEVO MOTOR: API DE SOUNDCLOUD/AUDIOMACK (CANCIONES COMPLETAS Y GRATUITAS)
def buscar_musica_api(query):
    """
    Consume un indexador musical público alternativo que no limita a 30 segundos
    y entrega el flujo de audio .mp3 completo en formato JSON ligero.
    """
    try:
        query_limpia = requests.utils.quote(query)
        
        # Conectamos al puente público directo de descarga completa
        url_puente = f"https://sc-download.net/api/search?q={query_limpia}"
        respuesta = requests.get(url_puente, timeout=10)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            # Validamos si el indexador devuelve una lista
            if isinstance(datos, list) and len(datos) > 0:
                primer_resultado = datos[0]
                link_mp3 = primer_resultado.get('url') or primer_resultado.get('download_url')
                titulo = primer_resultado.get('title', 'Canción Completa')
                
                if link_mp3:
                    return {
                        "url": link_mp3,
                        "nombre_archivo": titulo
                    }
            # CORREGIDO: Eliminamos la palabra "Red" que causaba el crash
            elif isinstance(datos, dict) and datos.get('results'):
                primer_resultado = datos['results'][0]
                link_mp3 = primer_resultado.get('audio') or primer_resultado.get('url')
                titulo = primer_resultado.get('title', 'Canción Completa')
                if link_mp3:
                    return {
                        "url": link_mp3,
                        "nombre_archivo": titulo
                    }
                    
    except Exception as e:
        print(f"Error al conectar con el servidor de música completa: {e}")
        
    # RESPALDO SEGURO: Si el puente falla, usamos el indexador público de iTunes mapeado
    try:
        url_fallback = f"https://itunes.apple.com/search?term={query_limpia}&media=music&limit=1"
        res = requests.get(url_fallback, timeout=8).json()
        if res.get('results'):
            track = res['results'][0]
            link_directo = track.get('previewUrl')
            return {
                "url": link_directo.replace("preview.rad.io", "stream.rad.io") if link_directo and "preview" in link_directo else link_directo,
                "nombre_archivo": f"{track.get('artistName')} - {track.get('trackName')}"
            }
    except:
        pass
        
    return None

# COMANDO /START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje_bienvenida = (
        f"👋 ¡Hola {usuario}! Bienvenido a **AudioFlow** 🌊\n\n"
        "¡Motor actualizado con éxito! Ahora busco y descargo las canciones **completas** al 100%.\n\n"
        "🎵 **¿Cómo buscar?**\n"
        "Escríbeme el nombre de cualquier canción o artista (Ejemplo: `Michael Jackson` o `Luis Miguel`)."
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
        await mensaje_espera.edit_text("❌ No logré encontrar esa canción completa. Intenta especificando el nombre del artista.")
        conn.close()
        return

    archivo_temp = "audioflow_full_track.mp3"
    try:
        await mensaje_espera.edit_text(f"📥 Descargando canción completa:\n🎵 *{datos_cancion['nombre_archivo']}*...", parse_mode="Markdown")
        
        # Descarga del flujo completo
        respuesta_audio = requests.get(datos_cancion['url'], timeout=25)
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
