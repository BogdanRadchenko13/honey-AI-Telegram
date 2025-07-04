import threading
import telebot  
import g4f  
import re
from PIL import Image
import pytesseract
import io  
from flask import Flask
import requests
  
# 🔐 Вставь сюда свой токен Telegram бота  
bot = telebot.TeleBot("7475051001:AAFUXqOC6UkdmjqKUleGLyNBjo0DCLIew50")  # Замени на свой  
OPENWEATHER_API_KEY = "397404f6e2154b5697d1ac3ddb51da5b"

# 🧠 Словарь для хранения истории сообщений каждого пользователя  
user_memory = {}  
  
# 🎨 Функция для стилизации ответа  
def stylize_response(text):  
    text = text.replace("ChatGPT", "Honey AI")  
    text = text.replace("OpenAI", "Honey Tech")  
    text = re.sub(r'\n{2,}', '\n', text)  
    sentences = re.split(r'(?<=[.?!])\s+', text)  
  
    blocks = []  
    block = []  
  
    for sentence in sentences:  
        block.append(sentence)  
        if len(block) == 2:  
            paragraph = ' '.join(block).strip()  
            match = re.match(r"^([^\s]{2,}(?:\s+[^\s]{2,}){0,2})", paragraph)  
            if match:  
                bold_part = f"<b>{match.group(1)}</b>"  
                paragraph = bold_part + paragraph[len(match.group(1)):]  
            blocks.append(paragraph)  
            block = []  
  
    if block:  
        paragraph = ' '.join(block).strip()  
        match = re.match(r"^([^\s]{2,}(?:\s+[^\s]{2,}){0,2})", paragraph)  
        if match:  
            bold_part = f"<b>{match.group(1)}</b>"  
            paragraph = bold_part + paragraph[len(match.group(1)):]  
        blocks.append(paragraph)  
  
    final_text = '\n\n'.join(blocks)  
    final_text = re.sub(r"`([^`]+)`", r"<code>\1</code>", final_text)  
    return final_text  

def smart_search(query):
    # 1️⃣ Wikipedia
    if query.lower().startswith("что такое") or query.lower().startswith("кто такой"):
        result = search_wikipedia(query)
        if result:
            return f" <b> Wikipedia:</b>\n\n{result}"

    # 2️⃣ Погода
    if "погода" in query.lower() or "температура" in query.lower():
        result = search_weather(query)
        if result:
            return f" <b>Прогноз погоды:</b>\n\n{result}"

    # 3️⃣ DuckDuckGo
    result = search_duckduckgo(query)
    if result:
        return f" <b>DuckDuckGo:</b>\n\n{result}"

    return " ERROR: Nothing found."

def search_wikipedia(query):
    title = query.replace("что такое", "").replace("кто такой", "").strip()
    url = f"https://ru.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        return data.get("extract")
    return None

def search_weather(query):
    city_match = re.search(r"(в|у|по)\s([А-Яа-яA-Za-z\- ]+)", query)
    city = city_match.group(2).strip() if city_match else "Киев"

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"{city}: {temp}°C, {desc}"
    return None

def search_duckduckgo(query):
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
    res = requests.get(url).json()
    if res.get("AbstractText"):
        return res["AbstractText"]
    elif "RelatedTopics" in res and res["RelatedTopics"]:
        return res["RelatedTopics"][0].get("Text")
    return None

# 🔸 Приветствие  
@bot.message_handler(commands=['start'])  
def send_welcome(message):  
    name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()  
    pic = 'https://i.postimg.cc/V6dnfVr5/file-00000000dd7461f4b9c5afdddf9102c0.png'  
    caption = f" Привет, {name}!\n\n Это Чат-Бот с Искусственным интеллектом прямо в Telegram! Просто введи интересующий тебя вопрос, и наш ИИ ответит."  
    bot.send_photo(message.chat.id, photo=pic, caption=caption)  

app = Flask('')

@app.route('/')
def home():
    return "✅ Бот работает!"

def run():
    app.run(host='0.0.0.0', port=8080)

# --- Запуск Flask в отдельном потоке ---
def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# ♻️ Очистка памяти  
@bot.message_handler(commands=['reset'])  
def reset_memory(message):  
    user_memory.pop(message.from_user.id, None)  
    bot.send_message(message.chat.id, " ♻️ Память сброшена.")  

@bot.message_handler(commands=['code'])
def handle_code_request(message):
    user_input = message.text.replace("/code", "").strip()

    if not user_input:
        bot.reply_to(message, "ERROR: Enter offer after /code")
        return

    loading = bot.send_message(message.chat.id, "Запрос генерируется...")

    try:
        # Подготавливаем запрос как к ИИ
        messages = [
            {"role": "system", "content": "Ты — HoneyAI. Ты пишешь чистый, понятный код без лишнего текста. Просто код."},
            {"role": "user", "content": user_input}
        ]

        response = g4f.ChatCompletion.create(
            model=g4f.models.default,
            messages=messages
        )

        bot.delete_message(message.chat.id, loading.message_id)

        # Если в ответе уже есть блок кода — оставим, иначе обернём вручную
        if "```" not in response:
            formatted = f"<pre><code>{response}</code></pre>"
        else:
            # Заменяем Markdown блоки на HTML
            formatted = response.replace("```python", "<pre><code>").replace("```", "</code></pre>")

        bot.send_message(message.chat.id, formatted, parse_mode="HTML")

    except Exception as e:
        bot.delete_message(message.chat.id, loading.message_id)
        bot.send_message(message.chat.id, f" ERROR: {e}")

@bot.message_handler(commands=['search'])
def handle_search(message):
    query = message.text.replace("/search", "").strip()
    if not query:
        bot.reply_to(message, "❗ Введите запрос после команды /search.")
        return
    bot.send_chat_action(message.chat.id, 'typing')
    reply = smart_search(query)
    bot.send_message(message.chat.id, reply, parse_mode="HTML")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    loading = bot.send_message(message.chat.id, " Запрос генерируется...")

    try:
        # Загружаем изображение
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        image = Image.open(io.BytesIO(downloaded_file))

        # Распознаём текст
        extracted_text = pytesseract.image_to_string(image, lang='eng+rus')

        if message.caption:
            prompt = f"{message.caption.strip()}\n\nВот распознанный текст задания:\n{extracted_text.strip()}"
        else:
            prompt = f"Реши следующее задание:\n{extracted_text.strip()}"

        # Обработка истории
        user_id = message.from_user.id
        if user_id not in user_memory:
            user_memory[user_id] = [
                {"role": "system", "content": "Your name is honeyAI. You don't have to mention that you are ChatGPT or openAI. You help with code, schoolwork, and ideas."}
            ]

        user_memory[user_id].append({"role": "user", "content": prompt})

        response = g4f.ChatCompletion.create(
            model=g4f.models.default,
            messages=user_memory[user_id]
        )

        user_memory[user_id].append({"role": "assistant", "content": response})

        bot.delete_message(message.chat.id, loading.message_id)

        reply = stylize_response(response)
        bot.send_message(message.chat.id, reply, parse_mode="HTML")

    except Exception as e:
        # Безопасное удаление сообщения
        try:
            bot.delete_message(message.chat.id, loading.message_id)
        except:
            pass
        bot.send_message(message.chat.id, f" ERROR: {str(e)}")

# 🔹 Обработка текстов с памятью  
@bot.message_handler(content_types=['text'])  
def handle_text(message):  
    try:
        user_id = message.from_user.id  
        user_input = message.text.strip()  
  
        Loading_message = bot.reply_to(message, " Запрос генерируется...")

        if message.text.lower() == "/reset":  
            reset_memory(message)  
            return  
  
        if user_id not in user_memory:  
            user_memory[user_id] = [  
                {"role": "system", "content": "Your name is honeyAI. You were created by the company honey Studio, and more specifically - Bogdan Radchenko. You don't have to mention that you are ChatGPT or openAI. You easily help with codes and homework. You can: generate texts, come up with ideas, are good at computer science, etc. You know and can speak 50 languages of the world, including: English, Russian, Ukrainian, French, Spanish, German, Chinese, Japanese, Korean, Arabic, Polish, Czech, Serbian, Bulgarian."}  
            ]  
  
        user_memory[user_id].append({"role": "user", "content": user_input})  
  
        try:  
            response = g4f.ChatCompletion.create(  
                model=g4f.models.default,  
                messages=user_memory[user_id]  
            )  
  
            user_memory[user_id].append({"role": "assistant", "content": response})  
  
            reply = stylize_response(response)  
        
            bot.delete_message(message.chat.id, Loading_message.message_id)

            bot.send_message(message.chat.id, reply, parse_mode="HTML")  
  
        except Exception as e:  
            bot.delete_message(message.chat.id, Loading_message.message_id)
            bot.send_message(message.chat.id, f" ERROR: {str(e)}")  
    finally:
        print("[ OK ] Service restarted.")
  
# ▶️ Запуск  
keep_alive()
bot.polling(none_stop=True)
