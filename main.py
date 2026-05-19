import os
import sqlite3
import random
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# CONFIGURACIÓN PRINCIPAL
TOKEN = "8294251191:AAETFtC3suGk5W9PP4kRVk-_OQuCGTO9CkI"

# COLECCIÓN LOCAL DE SABIDURÍA (Frases de alto impacto y viralidad)
FRASES_EMPRENDIMIENTO = [
    {"texto": "La paciencia es amarga, pero su fruto es dulce.", "autor": "Jean-Jacques Rousseau"},
    {"texto": "No es que tengamos poco tiempo, sino que perdemos mucho.", "autor": "Séneca"},
    {"texto": "El hombre que mueve montañas empieza quitando piedras pequeñas.", "autor": "Confucio"},
    {"texto": "Te conviertes en lo que le das a tu mente.", "autor": "Marco Aurelio"},
    {"texto": "El dinero sigue a la atención. Si controlas el enfoque de la gente, controlas los mercados.", "autor": "Mentalidad de Crecimiento"},
    {"texto": "El secreto para salir adelante es comenzar.", "autor": "Mark Twain"},
    {"texto": "La disciplina es el puente entre las metas y los logros.", "autor": "Jim Rohn"},
    {"texto": "No busques que las cosas sucedan como tú quieres, sino desea que sucedan tal como ocurren.", "autor": "Epicteto"}
]

# INICIALIZACIÓN DE LA BASE DE DATOS (Para guardar el registro de usuarios)
def iniciar_db():
    conn = sqlite3.connect('usuarios_flow.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            nombre TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# MOTOR CLÁSICO: BUSCADOR DE POEMAS (API Pública de Literatura Abierta)
def buscar_poema_api(autor_o_titulo):
    try:
        autor_limpio = requests.utils.quote(autor_o_titulo)
        # Consultamos el repositorio global de lírica abierta
        url = f"https://poetrydb.org/author,title/{autor_limpio};"
        # Si no encuentra por autor exacto, buscamos de forma general
        if not author_o_titulo:
            url = "https://poetrydb.org/title/Love"
            
        respuesta = requests.get(f"https://poetrydb.org/title/{autor_limpio}", timeout=6).json()
        
        if isinstance(respuesta, list) and len(respuesta) > 0:
            poema = respuesta[0]
            lineas = poema.get('lines', [])[:15] # Tomamos las primeras 15 líneas para que sea estético en Telegram
            texto_poema = "\n".join(lineas)
            return {
                "titulo": poema.get('title', 'Poema Hermoso'),
                "autor": poema.get('author', 'Autor Clásico'),
                "contenido": texto_poema
            }
    except Exception as e:
        print(f"Error al traer lírica externa: {e}")
    return None

# COMANDO /START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    uid = update.effective_user.id
    
    # Registramos al usuario en la base de datos local
    conn = sqlite3.connect('usuarios_flow.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO usuarios (id, nombre) VALUES (?, ?)", (uid, usuario))
        conn.commit()
    except:
        pass
    conn.close()

    mensaje = (
        f"✨ **¡Hola, {usuario}! Bienvenido a AudioFlow Inspiración** 🌊\n\n"
        "Soy tu asistente literario de alta fidelidad. Estoy listo para enviarte poemas, frases de sabiduría estoica y reflexiones para tus redes.\n\n"
        "⚡ **¿Qué puedo hacer por ti?**\n"
        "• Escribe **'frase'** o presiona /frase para recibir una dosis de mentalidad y sabiduría.\n"
        "• Escribe el nombre de un concepto o autor para buscar un poema completo.\n"
        "• *Ejemplo:* `Ode` o `Shakespeare`"
    )
    await update.message.reply_text(mensaje, parse_mode="Markdown")

# COMANDO /FRASE O TEXTO 'FRASE'
async def enviar_frase_diaria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    frase = random.choice(FRASES_EMPRENDIMIENTO)
    
    # Estructuramos el panel interactivo con tus enlaces premium de Monetag
    botones = [
        [InlineKeyboardButton("🎨 Descargar en Imagen Estética para WhatsApp", url="https://www.google.com")], # <-- AQUÍ PEGAS TU SMART LINK
        [InlineKeyboardButton("📚 Obtener Audiolibro Recomendado Gratis", url="https://www.google.com")]   # <-- AQUÍ PEGAS TU SMART LINK
    ]
    markup = InlineKeyboardMarkup(botones)
    
    mensaje_estetico = (
        f"📝 **Reflexión del Momento:**\n\n"
        f"💬 *\"{frase['texto']}\"*\n\n"
        f"✍️ — **{frase['autor']}**\n\n"
        f"🌿 _Usa los botones de abajo para obtener complementos multimedia en alta calidad:_ Jens"
    )
    
    await update.message.reply_text(mensaje_estetico, parse_mode="Markdown", reply_markup=markup)

# PROCESADOR CENTRAL DE TEXTO (Diferencia si pide frase o poema)
async def procesar_mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text.strip().lower()
    
    if not texto_usuario or texto_usuario.startswith('/'):
        return

    # Si el usuario pide explícitamente una frase corta
    if texto_usuario in ["frase", "frases", "motivacion", "estoico"]:
        await enviar_frase_diaria(update, context)
        return

    mensaje_espera = await update.message.reply_text("🔄 **Buscando piezas literarias en los registros abiertos...**")

    # Intentamos buscar un poema con el término del usuario
    poema = buscar_poema_api(texto_usuario)
    
    if not poema:
        # Si no encuentra un poema, le regala una frase de sabiduría para que el bot nunca lo deje vacío
        frase = random.choice(FRASES_EMPRENDIMIENTO)
        botones = [[InlineKeyboardButton("🎨 Obtener Fondo Estético HD", url="https://www.google.com")]] # <-- TU SMART LINK
        markup = InlineKeyboardMarkup(botones)
        
        await mensaje_espera.edit_text(
            f"💡 *No localicé un poema exacto, pero te dejo esta joya de sabiduría:*\n\n"
            f"» \"{frase['texto']}\"\n\n"
            f"✍️ — **{frase['autor']}**",
            reply_markup=markup
        )
        return

    # Si encuentra el poema, arma la tarjeta interactiva
    botones = [
        [InlineKeyboardButton("🖼️ Descargar Poema en Plantilla de Diseño", url="https://www.google.com")], # <-- TU SMART LINK
        [InlineKeyboardButton("📢 Compartir en mi Canal de Telegram", url="https://t.me/share/url?url=Mira%20este%20bot%20de%20poesia%20@audioflow_music_bot")]
    ]
    markup = InlineKeyboardMarkup(botones)

    await mensaje_espera.edit_text(
        f"📜 🏛️ **¡Obra Encontrada!**\n\n"
        f"📖 **Título:** {poema['titulo']}\n"
        f"✍️ **Autor:** {poema['autor']}\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"{poema['contenido']}\n\n"
        f"🍃 *(Mostrando fragmento optimizado)*\n\n"
        f"👇 *Usa los botones para descargar o compartir:*",
        reply_markup=markup
    )

# ARRANQUE DEL BOT
def main():
    iniciar_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("frase", enviar_frase_diaria))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensajes))

    print("AudioFlow Poesía y Sabiduría corriendo a coste cero...")
    application.run_polling()

if __name__ == '__main__':
    main()
