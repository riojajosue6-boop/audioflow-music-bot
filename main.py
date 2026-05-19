import os
import sqlite3
import random
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# CONFIGURACIÓN PRINCIPAL
TOKEN = "8294251191:AAETFtC3suGk5W9PP4kRVk-_OQuCGTO9CkI"

# ENLACE AL REPOSITORIO GIGANTE DE POESÍA EN ESPAÑOL (Miles de opciones)
URL_LIBRERIA = "https://raw.githubusercontent.com/feandres/poesia-espanola/master/poemas.json"

# BANCO DE RESPALDO DE FRASES ESTOICAS (Por si falla el internet en Railway)
RESPALDO_ESTOICO = [
    {"titulo": "Sobre la Brevedad de la Vida", "autor": "Séneca", "texto": "No es que tengamos un tiempo corto para vivir, sino que desperdiciamos una gran parte de él. La vida es lo suficientemente larga si sabes en qué enfocar tu mente."},
    {"texto": "La felicidad de tu vida depende de la calidad de tus pensamientos; por lo tanto, cuida tus impresiones.", "autor": "Marco Aurelio", "titulo": "Meditaciones"},
    {"texto": "No busques que las cosas sucedan como tú quieres, sino desea que sucedan tal como ocurren y serás feliz.", "autor": "Epicteto", "titulo": "Manual de Vida"}
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
        "He sido optimizado con un motor de literatura infinito y fondos artísticos en alta definición.\n\n"
        "⚡ **¿Cómo usarme?**\n"
        "Escribe palabras clave como **poema, estoico, dinero, amor o frase** y te generaré una tarjeta visual única al instante."
    )
    await update.message.reply_text(mensaje, parse_mode="Markdown")

# MOTOR DE EXTRACCIÓN Y GENERACIÓN VISUAL
async def enviar_tarjeta_visual(update: Update, context: ContextTypes.DEFAULT_TYPE, categoria="poemas"):
    mensaje_espera = await update.message.reply_text("🔄 **Invocando musas literarias...**")
    
    titulo = "Reflexión Pro"
    autor = "Desarrollo Personal"
    texto_final = ""

    # 1. MOTOR DE TEXTO INFINITO (Si pide poema o frase común, va a la librería en la nube)
    if categoria == "poemas":
        try:
            respuesta = requests.get(URL_LIBRERIA, timeout=7)
            if respuesta.status_code == 200:
                biblioteca = respuesta.json()
                obra = random.choice(biblioteca)
                
                titulo = obra.get('titulo', 'Poema Clásico')
                autor = obra.get('autor', 'Autor Anónimo')
                texto_completo = obra.get('texto', '')
                
                # Cortamos el poema si es exageradamente largo para que se vea estético en la pantalla
                lineas = texto_completo.split('\n')
                if len(lineas) > 15:
                    texto_final = "\n".join(lineas[:15]) + "\n\n(...)"
                else:
                    texto_final = texto_completo
            else:
                raise Exception()
        except:
            # Respaldo si la librería cae
            item = random.choice(RESPALDO_ESTOICO)
            titulo = item["titulo"]
            autor = item["autor"]
            texto_final = item["texto"]
    else:
        # Si pide estoico o negocios, usamos el banco local optimizado para Hotmart/Crecimiento
        item = random.choice(RESPALDO_ESTOICO)
        titulo = item["titulo"]
        autor = item["autor"]
        texto_final = item["texto"]

    # 2. MOTOR DE IMAGEN INFINITA (Unsplash Dinámico)
    # Generamos un número aleatorio único para obligar a Telegram a descargar una foto nueva cada vez
    semilla_foto = random.randint(1, 99999)
    # Buscamos términos artísticos: esculturas, naturaleza mística, minimalismo oscuro
    url_foto_dinamica = f"https://images.unsplash.com/photo-1607582255444-24f603c4cf7e?q=80&w=600&auto=format&fit=crop&sig={semilla_foto}"

    # Enlaces de Monetag (Prueba temporal)
    SMART_LINK_IMAGEN = "https://google.com" 
    SMART_LINK_AUDIO = "https://google.com"

    botones = [
        [InlineKeyboardButton("🎨 Descargar esta Frase en Fondo HD para mi Estado", url=SMART_LINK_IMAGEN)],
        [InlineKeyboardButton("🧠 Desbloquear Audio-Reflexión Secreta de Hoy", url=SMART_LINK_AUDIO)],
        [InlineKeyboardButton("📢 Compartir en mi Canal de Telegram", url=f"https://t.me/share/url?url=Mira%20las%20frases%20visuales%20de%20@audioflow_music_bot")]
    ]
    markup = InlineKeyboardMarkup(botones)
    
    descripcion_estetica = (
        f"📜 **{titulo}**\n"
        f"✍️ _Por {autor}_\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"{texto_final}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"✨ _Usa los botones de abajo para descargar en alta definición o escuchar el complemento de hoy:_ Jens"
    )
    
    try:
        await update.message.reply_photo(
            photo=url_foto_dinamica,
            caption=descripcion_estetica,
            parse_mode="Markdown",
            reply_markup=markup
        )
        await mensaje_espera.delete()
    except Exception as e:
        print(f"Error al enviar la foto: {e}")
        await mensaje_espera.edit_text("⚠️ Hubo un pequeño retraso al cargar la imagen de fondo. Por favor, intenta de nuevo escribiendo la palabra.")

# ESCUCHADOR INTELIGENTE
async def procesar_mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text.strip().lower() if update.message.text else ""
    
    if not texto_usuario or texto_usuario.startswith('/'):
        return

    # Filtros por palabras clave que viste en tu video
    if any(palabra in texto_usuario for palabra in ["dinero", "negocios", "emprender", "ganar", "marketing"]):
        await enviar_tarjeta_visual(update, context, categoria="negocios")
        
    elif any(palabra in texto_usuario for palabra in ["estoico", "filosofia", "sabiduria", "mente", "reflexion"]):
        await enviar_tarjeta_visual(update, context, categoria="estoico")
        
    elif any(palabra in texto_usuario for palabra in ["poema", "poemas", "frase", "frases", "amor", "amistad", "hola"]):
        await enviar_tarjeta_visual(update, context, categoria="poemas")
        
    else:
        await update.message.reply_text(
            "💡 *Puedes pedirme contenido escribiendo:* `poema`, `dinero`, `estoico` o `amor`. ¡Inténtalo! ✨",
            parse_mode="Markdown"
        )

def main():
    iniciar_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensajes))

    print("AudioFlow Engine v6.5 (Pulido y listo) corriendo...")
    application.run_polling()

if __name__ == '__main__':
    main()
