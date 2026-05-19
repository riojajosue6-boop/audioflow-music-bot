import os
import sqlite3
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# CONFIGURACIÓN PRINCIPAL
TOKEN = "8294251191:AAETFtC3suGk5W9PP4kRVk-_OQuCGTO9CkI"

# BANCO DE IMÁGENES ESTÉTICAS (URLs directas de fotografía artística de Unsplash)
# Paisajes melancólicos, estatuas de mármol estoicas y fondos minimalistas oscuros
FONDOS_ESTETICOS = [
    "https://images.unsplash.com/photo-1607582255444-24f603c4cf7e?q=80&w=600&auto=format&fit=crop", # Estatua Clásica / Estoica
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=600&auto=format&fit=crop", # Paisaje de Naturaleza Profunda
    "https://images.unsplash.com/photo-1486848538113-ce1a4923fbc5?q=80&w=600&auto=format&fit=crop", # Minimalista Oscuro / Textura
    "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?q=80&w=600&auto=format&fit=crop", # Niebla y Montañas
    "https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?q=80&w=600&auto=format&fit=crop"  # Hojas sutiles / Contemplativo
]

# COLECCIÓN DE SABIDURÍA INTERNA
FRASES_FLOW = [
    {"texto": "La paciencia es amarga, pero su fruto es dulce.", "autor": "Jean-Jacques Rousseau"},
    {"texto": "No es que tengamos poco tiempo, sino que perdemos mucho.", "autor": "Séneca"},
    {"texto": "El hombre que mueve montañas empieza quitando piedras pequeñas.", "autor": "Confucio"},
    {"texto": "Te conviertes en lo que le das a tu mente.", "autor": "Marco Aurelio"},
    {"texto": "El dinero sigue a la atención. Si controlas el enfoque, dominas el mercado.", "autor": "Mentalidad de Crecimiento"},
    {"texto": "La disciplina es el puente entre tus metas y tus logros cotidianos.", "autor": "Jim Rohn"},
    {"texto": "No busques que las cosas sucedan como tú quieres, sino acepta cómo ocurren.", "autor": "Epicteto"}
]

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

# COMANDO /START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    uid = update.effective_user.id
    
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
        "Soy tu motor de contenido estético visual para tus redes.\n\n"
        "⚡ **¿Cómo empezar?**\n"
        "Escribe la palabra **'frase'** o usa el comando /frase y te generaré una tarjeta visual lista para compartir."
    )
    await update.message.reply_text(mensaje, parse_mode="Markdown")

# TRANSMISOR VISUAL AUTOMÁTICO (IMAGEN + TEXTO)
async def enviar_tarjeta_visual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Seleccionamos contenido aleatorio para que cada interacción sea única
    frase = random.choice(FRASES_FLOW)
    imagen_fondo = random.choice(FONDOS_ESTETICOS)
    
    # ⚠️ CONFIGURACIÓN DE TU SISTEMA DE MONETIZACIÓN (MONETAG)
    # Cuando tengas tus Smart Links listos en Monetag, reemplaza "https://google.com" por tus enlaces privados.
    SMART_LINK_IMAGEN = "https://google.com" 
    SMART_LINK_AUDIO = "https://google.com"

    botones = [
        [InlineKeyboardButton("🎨 Descargar esta Frase en Fondo HD para mi Estado", url=SMART_LINK_IMAGEN)],
        [InlineKeyboardButton("🧠 Desbloquear Audio-Reflexión Secreta de Hoy", url=SMART_LINK_AUDIO)],
        [InlineKeyboardButton("📢 Compartir en mi Canal de Telegram", url=f"https://t.me/share/url?url=Mira%20las%20frases%20visuales%20de%20@audioflow_music_bot")]
    ]
    markup = InlineKeyboardMarkup(botones)
    
    # Formateamos el texto limpio como descripción (Caption) de la foto
    descripcion_estetica = (
        f"🏛️ **Reflexión y Sabiduría:**\n\n"
        f"💬 *\"{frase['texto']}\"*\n\n"
        f"✍️ — **{frase['autor']}**\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"✨ _Usa los botones de abajo para descargar en alta definición o escuchar el complemento de hoy:_ Jens"
    )
    
    # El bot envía la foto con el texto abajo, igual que el canal de la competencia
    await update.message.reply_photo(
        photo=imagen_fondo,
        caption=descripcion_estetica,
        parse_mode="Markdown",
        reply_markup=markup
    )

# ESCUCHADOR DE MENSAJES
async def procesar_mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text.strip().lower() if update.message.text else ""
    
    if not texto_usuario or texto_usuario.startswith('/'):
        return

    # Si escribe "frase" o cualquier palabra clave, activa la tarjeta visual
    if texto_usuario in ["frase", "frases", "motivacion", "estoico", "amor", "poema"]:
        await enviar_tarjeta_visual(update, context)
    else:
        # Si escribe otra cosa, le recordamos amablemente cómo usarlo para mantener el tráfico activo
        await update.message.reply_text(
            "💡 **Escribe la palabra 'frase'** para recibir tu dosis diaria de inspiración visual instantánea. ✨"
        )

def main():
    iniciar_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("frase", enviar_tarjeta_visual))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensajes))

    print("AudioFlow Visual Engine v4 corriendo sin costos...")
    application.run_polling()

if __name__ == '__main__':
    main()
