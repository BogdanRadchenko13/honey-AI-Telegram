import threading
import telebot  
import g4f  
from g4f.client import Client
from g4f.models import gpt_4
import re
from PIL import Image
import pytesseract
import io  
from flask import Flask
import requests
from telebot import types
import colorama
from colorama import *

init()
  
client = Client()

# 🔐 Вставь сюда свой токен Telegram бота  
bot = telebot.TeleBot("7475051001:AAFUXqOC6UkdmjqKUleGLyNBjo0DCLIew50")  # Замени на свой  

# 🧠 Словарь для хранения истории сообщений каждого пользователя  
user_memory = {}  
user_prompts = {}
  
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

def clean_text_output(text, max_paragraphs=3):
    # 1. Deleting LaTeX
    text = re.sub(r'\\\(|\\\)|\\\[|\\\]', '', text)
    text = re.sub(r'\$.*?\$', '', text)  # Убираем $...$
    text = re.sub(r'\\frac\{(.*?)\}\{(.*?)\}', r'\1 / \2', text)

    # 2. Remove system sound
    text = re.sub(r'(Started thinking|Analyzing.*?|Done in \d+s)', '', text, flags=re.IGNORECASE)

    # 3. Remove Markdown trash
    text = re.sub(r'[`*_#]', '', text)

    # 4. text to promt
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    # 5. Group 3–4 promts
    paragraphs = []
    buffer = []

    for s in sentences:
        buffer.append(s)
        if len(buffer) >= len(sentences) // max_paragraphs:
            paragraphs.append(' '.join(buffer).strip())
            buffer = []

    if buffer:
        paragraphs.append(' '.join(buffer).strip())

    #6.
    final = '\n\n'.join(paragraphs[:max_paragraphs])

    # 7. Lists
    final = re.sub(r'(?<!\n)(\s*\d+\.\s+)', r'\n\1', final)
    final = re.sub(r'(?<!\n)(\s*–\s+)', r'\n\1', final)

    # 8. Final remove two \n
    final = re.sub(r'\n{3,}', '\n\n', final)

    return final.strip()

def smart_search(query):
    normalized = query.lower().strip()
    
    wiki_triggers = [
        # Russian / Ukrainian
        "что такое", "кто такой", "що таке", "хто такий",
        # English
        "what is", "who is",
        # France
        "qu'est-ce que", "qui est",
        # Spain
        "qué es", "quién es",
        # Germany
        "was ist", "wer ist",
        # China
        "是什么",  # what is
        # Japanese
        "とは", "誰",
        # Korean
        "무엇입니까", "누구입니까",
        # Arabic
        "ما هو", "من هو",
        # Polish
        "co to jest", "kto to"
    ]
    
    # Wikipedia
    if any(trigger in normalized for trigger in wiki_triggers):
        result = search_wikipedia(query)
        if result:
            return f" <b> Wikipedia:</b>\n\n{result}"

    # DuckDuckGo
    result = search_duckduckgo(query)
    if result:
        return f" <b>DuckDuckGo:</b>\n\n{result}"

    return " ERROR: Nothing found."

def search_wikipedia(query):
    query_lower = query.lower()

    language_map = {
        "что такое": "ru",
        "кто такой": "ru",
        "що таке": "uk",
        "хто такий": "uk",
        "what is": "en",
        "who is": "en",
        "qu'est-ce que": "fr",
        "qui est": "fr",
        "qué es": "es",
        "quién es": "es",
        "was ist": "de",
        "wer ist": "de",
        "co to jest": "pl",
        "kto to": "pl",
        "ما هو": "ar",
        "من هو": "ar",
        "是什么": "zh",
        "誰": "ja",  # "who" in japanese
        "とは": "ja",
        "누구입니까": "ko",
        "무엇입니까": "ko"
    }

    # Search in Wikipedia
    wiki_lang = None
    for phrase, lang in language_map.items():
        if phrase in query_lower:
            wiki_lang = lang
            query = query_lower.replace(phrase, '').strip()
            break

    if not wiki_lang:
        return None

    # response
    api_url = f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
    res = requests.get(api_url)

    if res.status_code == 200:
        data = res.json()
        return data.get("extract")

    return None

def search_duckduckgo(query):
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
    res = requests.get(url).json()
    if res.get("AbstractText"):
        return res["AbstractText"]
    elif "RelatedTopics" in res and res["RelatedTopics"]:
        return res["RelatedTopics"][0].get("Text")
    return None

# Start message 
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
        bot.reply_to(message, " ERROR: Enter offer after /code")
        return

    loading = bot.send_message(message.chat.id, " Запрос генерируется...")

    try:
        # Response
        messages = [
            {"role": "system", "content": "Ты — HoneyAI. Ты пишешь чистый, понятный код без лишнего текста. Просто код."},
            {"role": "user", "content": user_input}
        ]

        response = g4f.ChatCompletion.create(
            model=g4f.models.default,
            messages=messages
        )

        bot.delete_message(message.chat.id, loading.message_id)

        # if Markdown not found - adding, else:
        if "```" not in response:
            formatted = f"<pre><code>{response}</code></pre>"
        else:
            # Markdown -> HTML
            formatted = response.replace("```python", "<pre><code>").replace("```", "</code></pre>")

        bot.send_message(message.chat.id, formatted, parse_mode="HTML")

    except Exception as e:
        bot.delete_message(message.chat.id, loading.message_id)
        bot.send_message(message.chat.id, f" ERROR: {e}")

@bot.message_handler(commands=['search'])
def handle_search(message):
    query = message.text.replace("/search", "").strip()
    if not query:
        bot.reply_to(message, " Введите запрос после команды /search.")
        return
    bot.send_chat_action(message.chat.id, 'typing')
    reply = smart_search(query)
    bot.send_message(message.chat.id, reply, parse_mode="HTML")

@bot.message_handler(commands=["image"])
def ask_enhancement(message):
    chat_id = message.chat.id
    prompt = message.text.replace("/image", "").strip()

    if not prompt:
        bot.send_message(chat_id, "Usage: /image your description here.")
        return

    # Сохраняем исходный промпт
    user_prompts[chat_id] = prompt

    # Отправляем кнопки выбора
    markup = types.InlineKeyboardMarkup()
    
    btn1 = types.InlineKeyboardButton("Включить🔥", callback_data="enhance_yes")
    btn2 = types.InlineKeyboardButton("Выключить 🔌", callback_data="enhance_no")

    markup.add(btn1)
    markup.add(btn2)
    
    bot.send_message(chat_id, " Желаете ли вы включить функцию улучшения промта при генерации изображения🔥? \n \n Это поможет сделать результат более точным и выразительным, добавит дополнительных деталей и повысит качество визуализации вашего запроса, однако эта функция ещё в разработке, по этому ИИ может - ошибаться. Подробно о том - как работает функция расписано здесь - https://telegra.ph/honeyAI-Generaciya-izobrazhenij-07-08.", reply_markup=markup, disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data in ["enhance_yes", "enhance_no"])
def handle_enhancement_choice(call):
    chat_id = call.message.chat.id
    prompt = user_prompts.get(chat_id)

    if not prompt:
        bot.send_message(chat_id, " ERROR: no prompt found.")
        return

    bot.edit_message_text("Generating image...", chat_id=chat_id, message_id=call.message.message_id)

    try:
        # if user's choice - "Yes" - Upgrade promt
        if call.data == "enhance_yes":
            prompt_response = client.chat.completions.create(
                model=gpt_4,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an assistant who transforms user queries in any language into detailed visual descriptions to generate images. Translate into English and add visual details. You don't comment with user!"
                        )
                    },
                    {"role": "user", "content": prompt}
                ]
            )
            prompt = prompt_response.choices[0].message.content.strip()

        print(Fore.CYAN + prompt + Fore.RESET)

        # Image creating
        image_response = client.images.generate(
            model="flux",
            prompt=prompt,
            response_format="url"
        )

        image_url = image_response.data[0].url

        # Loading picture
        img_data = requests.get(image_url).content
        with open("image.jpg", "wb") as f:
            f.write(img_data)

        # Sending
        with open("image.jpg", "rb") as f:
            bot.send_photo(chat_id, f)

    except Exception as e:
        bot.send_message(chat_id, f"Error:\n{e}")

    finally:
        user_prompts.pop(chat_id, None)  # clearning

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    loading = bot.send_message(message.chat.id, " Запрос генерируется...")

    try:
        # Pictures loading
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        image = Image.open(io.BytesIO(downloaded_file))

        # Pictures see
        extracted_text = pytesseract.image_to_string(image, lang='eng+rus')

        if message.caption:
            prompt = f"{message.caption.strip()}\n\nВот распознанный текст задания:\n{extracted_text.strip()}"
        else:
            prompt = f"Реши следующее задание:\n{extracted_text.strip()}"

        # Story
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
        # Deleting message
        try:
            bot.delete_message(message.chat.id, loading.message_id)
        except:
            pass
        bot.send_message(message.chat.id, f" ERROR: {str(e)}")

# Generation text + brain
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
                {"role": "system", "content": "Your name is honeyAI. You don't have to mention that you are ChatGPT or openAI. You easily help with codes and homework. You can: generate texts, come up with ideas, are good at computer science, etc. You know and can speak 50 languages of the world, including: English, Russian, Ukrainian, French, Spanish, German, Chinese, Japanese, Korean, Arabic, Polish, Czech, Serbian, Bulgarian."}  
            ]  
  
        user_memory[user_id].append({"role": "user", "content": user_input})  
  
        try:  
            response = g4f.ChatCompletion.create(  
                model=g4f.models.default,  
                messages=user_memory[user_id]  
            )  
  
            user_memory[user_id].append({"role": "assistant", "content": response})  
  
            reply = stylize_response(response) 
            reply = clean_text_output(reply) 
        
            bot.delete_message(message.chat.id, Loading_message.message_id)

            bot.send_message(message.chat.id, reply, parse_mode="HTML")  
  
        except Exception as e:  
            bot.delete_message(message.chat.id, Loading_message.message_id)
            bot.send_message(message.chat.id, f" ERROR: {str(e)}")  
    finally:
        print("[ OK ] Service restarted.")
  
# ▶️ launch
keep_alive()
bot.polling(none_stop=True)
