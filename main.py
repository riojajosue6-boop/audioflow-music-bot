import os
import sqlite3
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

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

# MOTOR FILTRADO: SOLO MÚSICA REPOSITORIO COMPLETO
def buscar_musica_inteligente(query):
    query_limpia = requests.utils.quote(query)
    nombre_corregido = ""
    
    # PASO 1: ADUANA DE CORRECCIÓN COMERCIAL (iTunes)
    try:
        url_corrector = f"https://itunes.apple.com/search?term={query_limpia}&media=music&limit=1"
        res_corrector = requests.get(url_corrector, timeout=6).json()
        
        if res_corrector.get('results') and len(res_corrector['results']) > 0:
            track_limpio = res_corrector['results'][0]
            nombre_corregido = f"{track_limpio.get('artistName')} - {track_limpio.get('trackName')}"
            print(f"🔮 Autocorregido: '{query}' -> '{nombre_corregido}'")
    except Exception as e:
        print(f"Error en aduana de corrección: {e}")

    # Si la aduana no pudo corregir el texto (errores extremos), usamos el texto original pero lo limpiamos
    if not nombre_corregido:
        nombre_corregido = query

    query_busqueda = requests.utils.quote(nombre_corregido)
    
    # INTENTO 1: Servidor global pero FILTRADO ESTRICTO A MÚSICA (Excluimos noticias, tv y programas)
    try:
        # Añadimos filtros como 'collection:audio_music' para evitar que se filtren programas de TV o radio viejos
        url_api = f"https://archive.org/advancedsearch.php?q={query_busqueda}+AND+mediatype:audio+AND+(collection:audio_music+OR+subject:music)&output=json&rows=2"
        respuesta = requests.get(url_api, timeout=8)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            docs = datos.get('response', {}).get('docs', [])
            
            for doc in docs:
                item_id = doc.get('identifier')
                titulo = doc.get('title', nombre_corregido)
                
                url_files = f"https://archive.org/metadata/{item_id}"
                res_files = requests.get(url_files, timeout=6).json()
                
                for f in res_files.get('files', []):
                    # El archivo debe ser MP3 original (evitamos pistas de 30 o 40 minutos de programas completos)
                    if f.get('name', '').lower().endswith('.mp3') and f.get('source', '') == 'original':
                        # Filtro de seguridad: si el archivo dura demasiado (más de 10 minutos en tamaño estimado), lo ignoramos
                        tamano = int(f.get('size', 0))
                        if tamano > 30000000: # Más de 30MB suele ser un programa de TV/Radio completo, no una canción
                            continue
                            
                        link_completo = f"https://archive.org/download/{item_id}/{f['name']}"
                        return {
                            "url": link_completo,
                            "nombre_archivo": titulo
                        }
    except Exception as e:
        print(f"Fallo en Archive Filtrado: {e}")
        
    # INTENTO 2 (RESPALDO EXCLUSIVO DE MÚSICA): API libre de Jamendo (Aquí es imposible que salgan programas de TV)
    try:
        url_respaldo = f"https://api.jamendo.com/v3.0/tracks/?client_id=56d30c95&format=json&limit=1&namesearch={query_busqueda}"
        res = requests.get(url_respaldo, timeout=8).json()
        
        if res.get('results') and len(res['results']) > 0:
            track = res['results'][0]
            if track.get('audio'):
                return {
                    "url": track.get('audio'),
                    "nombre_archivo": f"{track.get('artist_name')} - {track.get('name')}"
                }
    except Exception as e:
        print(f"Fallo en Jamendo: {e}")
        
    return None

# COMANDO /START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje_bienvenida = (
        f"👋 **¡Hola, {usuario}! Bienvenido de vuelta a AudioFlow** 🌊\n\n"
        "¡Filtros de purificación de música activados! 🧼🎵\n"
        "He sido configurado para bloquear programas de radio o televisión y entregarte **únicamente canciones de música reales**.\n\n"
        "📌 **Escríbeme el grupo y la canción que deseas escuchar.**\n"
        "✍️ *Ejemplo: La Oreja de Van Gogh - Rosas*"
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown")

# PROCESADOR INTERACTIVO DE BÚSQUEDA
async def procesar_musica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    busqueda_usuario = update.message.text.strip().lower()
    
    if not busqueda_usuario or busqueda_usuario.startswith('/'):
        return

    if len(busqueda_usuario) < 3:
        await update.message.reply_text(
            "⚠️ **Por favor, ingresa más detalles del grupo y la canción.**",
            parse_mode="Markdown"
        )
        return

    mensaje_espera = await update.message.reply_text("🔄 **Localizando pista de música, por favor espera...**", parse_mode="Markdown")

    # 1. VERIFICAR CACHÉ
    conn = sqlite3.connect('cache_musica.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM canciones WHERE busqueda = ?", (busqueda_usuario,))
    resultado = cursor.fetchone()

    if resultado:
        file_id_guardado = resultado[0]
        await mensaje_espera.edit_text("⚡ **¡Encontrada en caché! Enviando...**", parse_mode="Markdown")
        await update.message.reply_audio(audio=file_id_guardado)
        conn.close()
        await mensaje_espera.delete()
        return

    # 2. PROCESAR CON EL MOTOR DE FILTRADO MUSICAL STRICTO
    datos_cancion = buscar_musica_inteligente(busqueda_usuario)
    
    if not datos_cancion:
        await mensaje_espera.edit_text(
            "❌ **No logré encontrar esa canción.**\n\n"
            "💡 *Te sugiero escribir el nombre del grupo un poco más claro (Ej: Alex Ubago).*", 
            parse_mode="Markdown"
        )
        conn.close()
        return

    context.user_data['temp_track'] = datos_cancion
    context.user_data['temp_query'] = busqueda_usuario

    botones = [
        [InlineKeyboardButton("🎵 Descargar MP3 Completo", callback_data="download_mp3")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_download")]
    ]
    markup = InlineKeyboardMarkup(botones)

    await mensaje_espera.edit_text(
        f"🎯 **¡Canción Encontrada!**\n\n"
        f"🎵 **Título:** {datos_cancion['nombre_archivo']}\n"
        f"💿 **Tipo:** Archivo de Audio Musical\n\n"
        f"👇 *Confirma tu descarga haciendo clic abajo:*",
        parse_mode="Markdown",
        reply_markup=markup
    )
    conn.close()

# MANEJADOR DE CLICS
async def controlar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar_download":
        await query.message.edit_text("🚫 Descarga cancelada.")
        return

    if query.data == "download_mp3":
        datos_cancion = context.user_data.get('temp_track')
        busqueda_usuario = context.user_data.get('temp_query')

        if not datos_cancion:
            await query.message.edit_text("⚠️ Sesión expirada. Realiza la búsqueda de nuevo.")
            return

        await query.message.edit_text(f"📥 **Descargando audio musical:**\n🎬 *{datos_cancion['nombre_archivo']}*...", parse_mode="Markdown")

        archivo_temp = "audioflow_premium_track.mp3"
        try:
            respuesta_audio = requests.get(datos_cancion['url'], timeout=45, stream=True)
            
            if respuesta_audio.status_code == 200:
                with open(archivo_temp, "wb") as f:
                    for chunk in respuesta_audio.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                await query.message.edit_text("🚀 **¡Enviando reproductor musical!**", parse_mode="Markdown")
                
                with open(archivo_temp, "rb") as f:
                    mensaje_audio = await query.message.reply_audio(
                        audio=f, 
                        title=datos_cancion['nombre_archivo'],
                        caption="⚡ **Descargado por @audioflow_music_bot**\n\n⚠️ *Content can be removed at the request of the copyright holder.*",
                        parse_mode="Markdown"
                    )

                conn = sqlite3.connect('cache_musica.db')
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO canciones (busqueda, file_id, titulo) VALUES (?, ?, ?)",
                        (busqueda_usuario, mensaje_audio.audio.file_id, datos_cancion['nombre_archivo'])
                    )
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass
                conn.close()
                
                await query.message.delete()
            else:
                raise Exception("Error de respuesta de servidor.")

        except Exception as e:
            await query.message.reply_text("⚠️ El archivo musical no se pudo procesar. Intenta con otra canción.")
            print(f"Error interactivo crítico: {e}")
            
        finally:
            if os.path.exists(archivo_temp):
                os.remove(archivo_temp)

# ARRANQUE
def main():
    iniciar_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_musica))
    application.add_handler(CallbackQueryHandler(controlar_botones))

    print("AudioFlow Purificado corriendo...")
    application.run_polling()

if __name__ == '__main__':
    main()
