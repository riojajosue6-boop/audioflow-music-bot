
import os
import sqlite3
import random
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# CONFIGURACIÓN PRINCIPAL
TOKEN = "8294251191:AAETFtC3suGk5W9PP4kRVk-_OQuCGTO9CkI"

# ⚠️ COLOCA AQUÍ EL NOMBRE O ID DE TU CANAL PÚBLICO (Debe empezar con @)
# Ejemplo: "@mi_canal_de_poemas"
ID_CANAL = "@tu_canal_aqui" 

# ENLACE AL ALMACÉN GIGANTE DE LITERATURA EN ESPAÑOL (Archivo JSON público en GitHub)
URL_LIBRERIA = "https://raw.githubusercontent.com/feandres/poesia-espanola/master/poemas.json"

# BANCO DE ENLACES DE UNPLASH PARA IMÁGENES ARTÍSTICAS INFINITAS
# Usar "sig" con un número aleatorio hace que Unsplash devuelva una foto totalmente diferente en cada petición
URL_FOTO_ALEATORIA = "https://images.unsplash.com/photo-1607582255444-24f603c4cf7e?q=80&w=600&auto=format&fit=crop"

# FUNCIÓN QUE HACE EL TRABAJO AUTOMÁTICO (Cada 5 horas)
async def publicar_en_canal_automatico(context: ContextTypes.DEFAULT_TYPE):
    try:
        # 1. Traer la base de datos de poemas desde el repositorio en la nube
        respuesta = requests.get(URL_LIBRERIA, timeout=10)
        if respuesta.status_code == 200:
            biblioteca = respuesta.json()
            obra = random.choice(biblioteca) # Elige un poema al azar entre miles
            
            titulo = obra.get('titulo', 'Poema Clásico')
            autor = obra.get('autor', 'Autor Anónimo')
            texto_completo = obra.get('texto', '')
            
            # Cortamos el poema si es excesivamente largo para que quepa bien en la tarjeta de Telegram
            lineas = texto_completo.split('\n')
            if len(lineas) > 16:
                texto_final = "\n".join(lineas[:16]) + "\n\n(...)"
            else:
                texto_final = texto_completo
        else:
            raise Exception("No se pudo conectar a la librería de respaldo.")
            
    except Exception as e:
        print(f"Error al extraer poema de la librería: {e}")
        # Respaldo estoico por si falla la conexión a la librería externa
        titulo = "Sobre la Serenidad"
        autor = "Séneca"
        texto_final = "No es que tengamos un tiempo corto para vivir,\nsino que desperdiciamos una gran parte de él.\nLa vida es lo suficientemente larga si estás enfocado."

    # 2. Generar URL de imagen artística única para este post
    semilla_aleatoria = random.randint(1, 9999)
    foto_unica = f"https://source.unsplash.com/featured/600x400/?sculpture,nature,dark&sig={semilla_aleatoria}"

    # ⚠️ CONFIGURACIÓN DE TU MONETIZACIÓN CON MONETAG
    SMART_LINK_IMAGEN = "https://google.com" 
    SMART_LINK_AUDIO = "https://google.com"

    botones = [
        [InlineKeyboardButton("🎨 Descargar esta Obra en Fondo HD para mi Estado", url=SMART_LINK_IMAGEN)],
        [InlineKeyboardButton("🧠 Desbloquear Audio-Reflexión Secreta de Hoy", url=SMART_LINK_AUDIO)]
    ]
    markup = InlineKeyboardMarkup(botones)

    # Formateamos la descripción estética idéntica a la competencia
    post_estetico = (
        f"📜 **{titulo}**\n"
        f"✍️ _Por {autor}_\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"{texto_final}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"✨ _Disfruta de la entrega automática de hoy. Usa los botones para más contenido:_ Jens"
    )

    try:
        # El bot lanza el mensaje directamente al Canal, no al chat privado
        await context.bot.send_photo(
            chat_id=ID_CANAL,
            photo=foto_unica,
            caption=post_estetico,
            parse_mode="Markdown",
            reply_markup=markup
        )
        print("¡Post automático enviado al canal con éxito!")
    except Exception as error:
        print(f"Error al enviar al canal. Asegúrate de que el bot sea ADMINISTRADOR: {error}")

# COMANDO /START PARA ACTIVAR EL TEMPORIZADOR
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    
    # Verificamos si la alarma ya está corriendo para no duplicarla
    job_en_curso = context.job_queue.get_jobs_by_name("alarma_5_horas")
    
    if not job_en_curso:
        # Programamos la tarea: primera ejecución en 2 segundos, y luego cada 5 horas (18000 segundos)
        context.job_queue.run_repeating(
            publicar_en_canal_automatico, 
            interval=18000, 
            first=2, 
            name="alarma_5_horas"
        )
        mensaje = f"🚀 **¡Hola {usuario}! Sistema AudioFlow Automatizado Activado.**\n\nA partir de este momento, publicaré un poema visual hermoso en el canal {ID_CANAL} cada 5 horas en piloto automático. ¡Ya puedes cerrar este chat!"
    else:
        mensaje = f"⏳ El sistema ya se encuentra activo y transmitiendo al canal {ID_CANAL} de forma automática."

    await update.message.reply_text(mensaje, parse_mode="Markdown")

def main():
    # Iniciamos la aplicación con soporte para JobQueue (Temporizadores)
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    print("AudioFlow Cron Engine v7 corriendo...")
    application.run_polling()

if __name__ == '__main__':
    main()
