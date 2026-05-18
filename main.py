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

# MOTOR DE AUDIO COMPLETO
def buscar_musica_api(query):
    try:
        query_limpia = requests.utils.quote(query)
        url_api = f"https://archive.org/advancedsearch.php?q={query_limpia}+AND+mediatype:audio&output=json&rows=1"
        respuesta = requests.get(url_api, timeout=12)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            docs = datos.get('response', {}).get('docs', [])
            if docs:
                item_id = docs[0].get('identifier')
                titulo = docs[0].get('title', 'Canción Completa')
                
                url_files = f"https://archive.org/metadata/{item_id}"
                res_files = requests.get(url_files, timeout=10).json()
                
                for f in res_files.get('files', []):
                    if f.get('name', '').endswith('.mp3'):
                        link_completo = f"https://archive.org/download/{item_id}/{f['name']}"
                        return {"url": link_completo, "nombre_archivo": titulo}
                        
    except Exception as e:
        print(f"Error en motor principal: {e}")
        
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
    except:
        pass
    return None

# COMANDO /START (MÁS AMABLE, INTUITIVO Y CON EJEMPLO CLARO)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje_bienvenida = (
        f"👋 **¡Hola, {usuario}! Qué alegría tenerte en AudioFlow** 🌊\n\n"
        "Te ayudaré a encontrar y descargar tus canciones favoritas completas y al instante. 🎧\n\n"
        "📌 **Por favor, escríbeme el nombre de la banda/grupo y la canción que quieres escuchar.**\n\n"
        "✍️ **Por ejemplo:**\n"
        "`Luis Miguel - Ahora te puedes marchar`\n"
        "`Guns N' Roses - Sweet Child O' Mine`\n\n"
        "¡Dime! ¿Qué temazo vamos a escuchar hoy? 🎶"
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown")

# PROCESADOR INTERACTIVO DE BÚSQUEDA
async def procesar_musica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    busqueda_usuario = update.message.text.strip().lower()
    
    if not busqueda_usuario or busqueda_usuario.startswith('/'):
        return

    # CONTROL AMABLE: Si escribe menos de 3 letras, le recordamos poner artista y canción
    if len(busqueda_usuario) < 3:
        await update.message.reply_text(
            "⚠️ **¡Oops! Falta un poquito más de información.**\n\n"
            "Por favor, escribe de forma más detallada el **grupo y la canción** para que pueda localizarla correctamente. 😉",
            parse_mode="Markdown"
        )
        return

    # Mensaje inicial estilizado
    mensaje_espera = await update.message.reply_text("🔄 **Buscando en los servidores...**\n⏳ *Por favor, dame unos segundos.*", parse_mode="Markdown")

    # 1. VERIFICAR CACHÉ
    conn = sqlite3.connect('cache_musica.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM canciones WHERE busqueda = ?", (busqueda_usuario,))
    resultado = cursor.fetchone()

    if resultado:
        file_id_guardado = resultado[0]
        await mensaje_espera.edit_text("⚡ **¡Canción localizada en caché!**\n🚀 *Enviando flujo de audio instantáneo...*", parse_mode="Markdown")
        await update.message.reply_audio(audio=file_id_guardado)
        conn.close()
        await mensaje_espera.delete()
        return

    # 2. ENCONTRAR EN LA API
    datos_cancion = buscar_musica_api(busqueda_usuario)
    
    if not datos_cancion:
        await mensaje_espera.edit_text(
            "❌ **No logré encontrar esa pista.**\n\n"
            "💡 *Te sugiero probar escribiendo el nombre del grupo seguido del título de la canción. ¡Así es infalible!*", 
            parse_mode="Markdown"
        )
        conn.close()
        return

    # Guardamos los datos temporalmente en el contexto del usuario
    context.user_data['temp_track'] = datos_cancion
    context.user_data['temp_query'] = busqueda_usuario

    # Crear panel de botones intuitivo
    botones = [
        [InlineKeyboardButton("🎵 Descargar MP3 Completo", callback_data="download_mp3")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_download")]
    ]
    markup = InlineKeyboardMarkup(botones)

    await mensaje_espera.edit_text(
        f"🎯 **¡Resultado Encontrado!**\n\n"
        f"🎵 **Título:** {datos_cancion['nombre_archivo']}\n"
        f"💿 **Calidad:** Alta Calidad / Estéreo\n\n"
        f"👇 *Haz clic abajo para confirmar tu descarga:*",
        parse_mode="Markdown",
        reply_markup=markup
    )
    conn.close()

# MANEJADOR DE CLICS EN LOS BOTONES
async def controlar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar_download":
        await query.message.edit_text("🚫 Descarga cancelada. ¡Cuando quieras puedes realizar otra búsqueda!")
        return

    if query.data == "download_mp3":
        datos_cancion = context.user_data.get('temp_track')
        busqueda_usuario = context.user_data.get('temp_query')

        if not datos_cancion:
            await query.message.edit_text("⚠️ La sesión expiró. Por favor ingresa el grupo y canción nuevamente.")
            return

        await query.message.edit_text(f"📥 **Descargando pista:**\n🎬 *{datos_cancion['nombre_archivo']}*\n\n🛜 *Preparando archivo de audio completo...*", parse_mode="Markdown")

        archivo_temp = "audioflow_premium_track.mp3"
        try:
            respuesta_audio = requests.get(datos_cancion['url'], timeout=35)
            with open(archivo_temp, "wb") as f:
                f.write(respuesta_audio.content)

            await query.message.edit_text("🚀 **¡Proceso completado con éxito!**\n📤 *Enviando reproductor multimedia...*", parse_mode="Markdown")
            
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

        except Exception as e:
            await query.message.reply_text("⚠️ Tuvimos un pequeño inconveniente en la descarga. Por favor intenta de nuevo.")
            print(f"Error interactivo: {e}")
            
        finally:
            if os.path.exists(archivo_temp):
                os.remove(archivo_temp)
            await query.message.delete()

# ARRANQUE
def main():
    iniciar_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_musica))
    application.add_handler(CallbackQueryHandler(controlar_botones))

    print("AudioFlow Amigable corriendo...")
    application.run_polling()

if __name__ == '__main__':
    main()
