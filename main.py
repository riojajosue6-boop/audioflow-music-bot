import os
import sqlite3
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# CONFIGURACIÓN PRINCIPAL
TOKEN = "8294251191:AAETFtC3suGk5W9PP4kRVk-_OQuCGTO9CkI"

# BANCO DE IMÁGENES AMPLIADO (Mármol, naturaleza y minimalismo oscuro)
FONDOS_ESTETICOS = [
    "https://images.unsplash.com/photo-1607582255444-24f603c4cf7e?q=80&w=600&auto=format&fit=crop", # Estatua Mármol
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=600&auto=format&fit=crop", # Paisaje Profundo
    "https://images.unsplash.com/photo-1486848538113-ce1a4923fbc5?q=80&w=600&auto=format&fit=crop", # Textura Oscura
    "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?q=80&w=600&auto=format&fit=crop", # Niebla
    "https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?q=80&w=600&auto=format&fit=crop", # Hojas sutiles
    "https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?q=80&w=600&auto=format&fit=crop", # Bosque místico
    "https://images.unsplash.com/photo-1472214222541-d510753a8707?q=80&w=600&auto=format&fit=crop"  # Atardecer suave
]

# BANCO DE FRASES CATEGORIZADO (Para responder de acuerdo a lo que escribe el usuario)
FRASES_CATEGORIAS = {
    "negocios": [
        {"texto": "El dinero sigue a la atención. Si controlas el enfoque, dominas el mercado.", "autor": "Mentalidad de Crecimiento"},
        {"texto": "La disciplina es el puente entre tus metas y tus logros cotidianos.", "autor": "Jim Rohn"},
        {"texto": "El secreto para salir adelante es comenzar.", "autor": "Mark Twain"},
        {"texto": "No encuentres clientes para tus productos, encuentra productos para tus clientes.", "autor": "Seth Godin"}
    ],
    "estoico": [
        {"texto": "No es que tengamos poco tiempo, sino que perdemos mucho.", "autor": "Séneca"},
        {"texto": "Te conviertes en lo que le das a tu mente.", "autor": "Marco Aurelio"},
        {"texto": "No busques que las cosas sucedan como tú quieres, sino acepta cómo ocurren.", "autor": "Epicteto"},
        {"texto": "La felicidad de tu vida depende de la calidad de tus pensamientos.", "autor": "Marco Aurelio"}
    ],
    "humanas": [
        {"texto": "La paciencia es amarga, pero su fruto es dulce.", "autor": "Jean-Jacques Rousseau"},
        {"texto": "El hombre que mueve montañas empieza quitando piedras pequeñas.", "autor": "Confucio"},
        {"texto": "La herida es el lugar por donde entra la luz.", "autor": "Rumi"},
        {"texto": "Conocerse a uno mismo es el principio de toda sabiduría.", "autor": "Aristóteles"}
    ]
}

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
        "Soy tu motor de contenido visual y reflexiones estéticas para tus redes.\n\n"
        "⚡ **¿Cómo interactuar?**\n"
        "Escribe palabras clave como **frase, estoico, dinero, negocios, amor o amistad** y te generaré una tarjeta única."
    )
    await update.message.reply_text(mensaje, parse_mode="Markdown")

# ENVIAR TARJETA VISUAL SIN REPETICIONES
async def enviar_tarjeta_visual(update: Update, context: ContextTypes.DEFAULT_TYPE, categoria="humanas"):
    # 1. Obtener lista de frases de la categoría elegida
    lista_frases = FRASES_CATEGORIAS.get(categoria, FRASES_CATEGORIAS["humanas"])
    
    # Inicializar el historial del usuario para evitar repeticiones en la sesión actual
    if 'ultima_frase' not in context.user_data:
        context.user_data['ultima_frase'] = None
    if 'ultimo_fondo' not in context.user_data:
        context.user_data['ultimo_fondo'] = None

    # Filtro inteligente para no repetir la frase anterior
    frases_disponibles = [f for f in lista_frases if f['texto'] != context.user_data['ultima_frase']]
    frase = random.choice(frases_disponibles if frases_disponibles else lista_frases)
    context.user_data['ultima_frase'] = frase['texto']

    # Filtro inteligente para no repetir la foto anterior
    fondos_disponibles = [img for img in FONDOS_ESTETICOS if img != context.user_data['ultimo_fondo']]
    imagen_fondo = random.choice(fondos_disponibles if fondos_disponibles else FONDOS_ESTETICOS)
    context.user_data['ultimo_fondo'] = imagen_fondo
    
    # ENLACES DE MONETAG (Coloca tus Smart Links aquí cuando gustes)
    SMART_LINK_IMAGEN = "https://google.com" 
    SMART_LINK_AUDIO = "https://google.com"

    botones = [
        [InlineKeyboardButton("🎨 Descargar esta Frase en Fondo HD para mi Estado", url=SMART_LINK_IMAGEN)],
        [InlineKeyboardButton("🧠 Desbloquear Audio-Reflexión Secreta de Hoy", url=SMART_LINK_AUDIO)],
        [InlineKeyboardButton("📢 Compartir en mi Canal de Telegram", url=f"https://t.me/share/url?url=Mira%20las%20frases%20visuales%20de%20@audioflow_music_bot")]
    ]
    markup = InlineKeyboardMarkup(botones)
    
    descripcion_estetica = (
        f"🏛 *Reflexión y Sabiduría:*\n\n"
        f"💬 *\"{frase['texto']}\"*\n\n"
        f"✍️ — **{frase['autor']}**\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"✨ _Usa los botones de abajo para descargar en alta definición o escuchar el complemento de hoy:_ Jens"
    )
    
    await update.message.reply_photo(
        photo=imagen_fondo,
        caption=descripcion_estetica,
        parse_mode="Markdown",
        reply_markup=markup
    )

# ESCUCHADOR INTELIGENTE POR TEMÁTICA
async def procesar_mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text.strip().lower() if update.message.text else ""
    
    if not texto_usuario or texto_usuario.startswith('/'):
        return

    # Mapeo inteligente de intenciones (Si detecta palabras clave, define la categoría)
    if any(palabra in texto_usuario for palabra in ["dinero", "negocios", "emprender", "ganar", "marketing"]):
        await enviar_tarjeta_visual(update, context, categoria="negocios")
        
    elif any(palabra in texto_usuario for palabra in ["estoico", "filosofia", "sabiduria", "mente", "reflexion"]):
        await enviar_tarjeta_visual(update, context, categoria="estoico")
        
    elif any(palabra in texto_usuario for palabra in ["frase", "frases", "amor", "amistad", "poema", "poemas", "humanas"]):
        await enviar_tarjeta_visual(update, context, categoria="humanas")
        
    else:
        # Respuesta si escribe algo completamente fuera del tema
        await update.message.reply_text(
            "💡 *Puedes pedirme contenido escribiendo:* `frase`, `dinero`, `estoico` o `amor`. ¡Inténtalo! ✨",
            parse_mode="Markdown"
        )

def main():
    iniciar_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("frase", lambda u, c: enviar_tarjeta_visual(u, c, "humanas")))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensajes))

    print("AudioFlow Engine v5 (Anti-Repetición) corriendo...")
    application.run_polling()

if __name__ == '__main__':
    main()
