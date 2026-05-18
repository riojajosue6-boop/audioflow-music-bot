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

# NUEVO MOTOR: API DE MÚSICA GRATUITA, ULTRA RÁPIDA Y ESTABLE (OPCIÓN B)
def buscar_musica_api(query):
    """
    Consume un indexador musical público que devuelve datos en formato JSON ligero.
    Cero consumo de recursos en Railway, sin riesgo de baneos de IP.
    """
    try:
        # Codificamos el texto para que sea seguro en una URL
        query_limpia = requests.utils.quote(query)
        
        # Usamos un indexador API público y gratuito de música (Basado en el catálogo libre de Deezer/Audiomack)
        url_api = f"https://api.deezer.com/search?q={query_limpia}&limit=1"
        
        respuesta = requests.get(url_api, timeout=8)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            if datos.get('data') and len(datos['data']) > 0:
                primer_resultado = datos['data'][0]
                
                # Extraemos los datos esenciales necesarios
                link_mp3 = primer_resultado.get('preview') # Enlace directo al stream/audio .mp3 libre
                titulo = primer_resultado.get('title_short', 'Canción')
                artista = primer_resultado.get('artist', {}).get('name', 'Artista')
                
                if link_mp3:
                    return {
                        "url": link_mp3,
                        "nombre_archivo": f"{artista} - {titulo}"
                    }
    except Exception as e:
        print(f"Error al conectar con el servidor de música: {e}")
    return None

# COMANDO /START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje_bienvenida = (
        f"👋 ¡Hola {usuario}! Bienvenido a la nueva versión de **AudioFlow** 🌊\n\n"
        "He sido actualizado a un motor de alta velocidad global. ¡Ahora sí busco y descargo al instante!\n\n"
        "🎵 **¿Cómo buscar?**\n"
        "Escríbeme el nombre de cualquier canción o artista (Ejemplo: `Luis Miguel Incondicional` o `Bad Bunny`)."
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown")

# PROCESADOR DE BÚSQUEDA Y ENTREGA (CON CACHÉ ACTIVADA)
async def procesar_musica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    busqueda_usuario = update.message.text.strip().lower()
    
    # Validar que no sea un texto vacío o un comando raro
    if not busqueda_usuario or busqueda_usuario.startswith('/'):
        return

    mensaje_espera = await update.message.reply_text("🔍 Buscando en los servidores musicales, por favor espera...")

    # 1. VERIFICAR SI LA CANCIÓN YA ESTÁ EN LA CACHÉ DE TELEGRAM
    conn = sqlite3.connect('cache_musica.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM canciones WHERE busqueda = ?", (busqueda_usuario,))
    resultado = cursor.fetchone()

    if resultado:
        # ¡Existe en caché! Se envía en 0.1 segundos sin descargar nada a Railway
        file_id_guardado = resultado[0]
        await mensaje_espera.edit_text("⚡ ¡Canción encontrada en caché! Enviando de inmediato...")
        await update.message.reply_audio(audio=file_id_guardado)
        conn.close()
        await mensaje_espera.delete()
        return

    # 2. SI NO ESTÁ EN CACHÉ, LE PEDIMOS EL LINK A LA API GRATUITA
    datos_cancion = buscar_musica_api(busqueda_usuario)
    
    if not datos_cancion:
        await mensaje_espera.edit_text("❌ No logré encontrar esa canción en el servidor. Intenta escribiendo el nombre de forma diferente o añade el artista.")
        conn.close()
        return

    archivo_temp = "audioflow_track.mp3"
    try:
        await mensaje_espera.edit_text(f"📥 Descargando flujo: {datos_cancion['nombre_archivo']}...")
        
        # Descargamos el archivo de la API de forma temporal
        respuesta_audio = requests.get(datos_cancion['url'], timeout=10)
        with open(archivo_temp, "wb") as f:
            f.write(respuesta_audio.content)

        await mensaje_espera.edit_text("🚀 Subiendo archivo de audio nativo a Telegram...")
        
        # Enviamos el archivo final al usuario en formato reproductor nativo
        with open(archivo_temp, "rb") as f:
            mensaje_audio = await update.message.reply_audio(
                audio=f, 
                title=datos_cancion['nombre_archivo'],
                caption="⚡ Descargado velozmente por @audioflow_music_bot\n\n⚠️ Content can be removed at the request of the copyright holder."
            )

        # 3. GUARDAR EL FILE_ID PARA EL FUTURO (SISTEMA CACHÉ INTELIGENTE)
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
        await update.message.reply_text("⚠️ Ocurrió un pequeño inconveniente al procesar el audio. Por favor intenta nuevamente.")
        print(f"Error en el proceso: {e}")
        
    finally:
        # Limpieza absoluta de temporales para mantener tu Railway intacto y limpio
        if os.path.exists(archivo_temp):
            os.remove(archivo_temp)
        conn.close()
        await mensaje_espera.delete()

# ARRANQUE OFICIAL DEL PROYECTO
def main():
    iniciar_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_musica))

    print("AudioFlow versión API está corriendo en vivo...")
    application.run_polling()

if __name__ == '__main__':
    main()
