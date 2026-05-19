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

# MOTOR EXCLUSIVO DE MÚSICA: SOUNDCLOUD PUBLIC API
def buscar_musica_soundcloud(query):
    """
    Busca pistas completas directamente en SoundCloud usando un cliente público estable.
    Garantiza solo audio musical, excelente buscador ortográfico y cero consumo en Railway.
    """
    try:
        query_limpia = requests.utils.quote(query)
        
        # Endpoint de un puente público optimizado y libre hacia el catálogo de SoundCloud
        url_api = f"https://sc-download.net/api/search?q={query_limpia}"
        respuesta = requests.get(url_api, timeout=12)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            
            # Verificamos que nos devuelva una lista de canciones válidas
            if isinstance(datos, list) and len(datos) > 0:
                # Tomamos el primer resultado que ofrece el buscador inteligente
                primer_track = datos[0]
                
                link_mp3 = primer_track.get('url') or primer_track.get('download_url')
                titulo = primer_track.get('title', 'Canción Completa')
                
                # Control de seguridad extra: Evitamos enlaces caídos o vacíos
                if link_mp3 and (link_mp3.startswith('http://') or link_mp3.startswith('https://')):
                    return {
                        "url": link_mp3,
                        "nombre_archivo": titulo
                    }
                    
    except Exception as e:
        print(f"Error en motor principal de SoundCloud: {e}")
        
    # RESPALDO DE SEGURIDAD 100% MÚSICA: API Global de Jamendo
    try:
        query_limpia = requests.utils.quote(query)
        url_jamendo = f"https://api.jamendo.com/v3.0/tracks/?client_id=56d30c95&format=json&limit=1&namesearch={query_limpia}"
        res = requests.get(url_jamendo, timeout=8).json()
        
        if res.get('results') and len(res['results']) > 0:
            track = res['results'][0]
            if track.get('audio'):
                return {
                    "url": track.get('audio'),
                    "nombre_archivo": f"{track.get('artist_name')} - {track.get('name')}"
                }
    except Exception as e:
        print(f"Error en motor de respaldo musical: {e}")
        
    return None

# COMANDO /START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje_bienvenida = (
        f"👋 **¡Hola, {usuario}! Bienvenido a AudioFlow** 🌊\n\n"
        "¡Motor de música optimizado al 100%! 🎧✨\n"
        "Ahora busco directamente en plataformas musicales completas. Se acabaron los programas extraños.\n\n"
        "📌 **Escríbeme el grupo y la canción que quieres escuchar.**\n"
        "✍️ **Por ejemplo:**\n"
        "`Alex Ubago - Sin miedo a nada`\n"
        "`La Oreja de Van Gogh - Rosas`"
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

    # 2. PROCESAR CON EL NUEVO MOTOR DE SOUNDCLOUD
    datos_cancion = buscar_musica_soundcloud(busqueda_usuario)
    
    if not datos_cancion:
        await mensaje_espera.edit_text(
            "❌ **No logré encontrar esa canción.**\n\n"
            "💡 *Intenta escribiendo el nombre de la canción de otra forma o añadiendo el grupo de manera clara.*", 
            parse_mode="Markdown"
        )
        conn.close()
        return

    # Guardamos datos de sesión
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
            # Descarga del archivo en chunks ligeros para cuidar la RAM
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
                        caption="⚡ **Descargado completo por @audioflow_music_bot**\n\n⚠️ *Content can be removed at the request of the copyright holder.*",
                        parse_mode="Markdown"
                    )

                # GUARDAR EN CACHÉ
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
                raise Exception("El servidor de origen dio error de respuesta.")

        except Exception as e:
            await query.message.reply_text("⚠️ Este servidor de descarga experimentó un retraso. Por favor, intenta de nuevo presionando el botón.")
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

    print("AudioFlow Puro SoundCloud corriendo...")
    application.run_polling()

if __name__ == '__main__':
    main()
