import subprocess
import pyttsx3
import speech_recognition as sr
import datetime
import os
import http.client
import time
import webbrowser
import pywhatkit
import pathlib
import pyautogui
import re
import pyperclip
import requests
from playsound3 import playsound
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import google.generativeai as genai
import wave
import json

engine = pyttsx3.init()
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)
engine.setProperty('rate', 150)
drive_letter = pathlib.Path.home().drive
current_user_name = os.getlogin()
chat_folder_index = 1
assistant_active = True
speaker_lang = 'en'
lang_idx = {"en": 0, "ru": 1, "uz": 2}.get(speaker_lang, 0)
query = ''
muxlisa_token = "I3AlBDpE-3rImcW8rUVd-GiHCOIHYPpcsZxYzY3c"

#gemini-model
genai.configure(api_key="AIzaSyBA3Iyu4ykecNupFkBzSo9C-JKCdFvHnOo")
model = genai.GenerativeModel("gemini-1.5-flash")

# Create the main window
root = ttk.Window(themename="flatly")
root.title('Jamila AI')
root.geometry('420x600+1250+350')
root.resizable(False, False)

# Add a scrollable frame for messages
frame_canvas = ttk.Frame(root)
frame_canvas.pack(fill="both", expand=True, padx=10, pady=10)

canvas = ttk.Canvas(frame_canvas)
scrollbar = ttk.Scrollbar(frame_canvas, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas)

def resize_canvas(event):
    # Adjust scroll region when the window is resized
    canvas.configure(scrollregion=canvas.bbox("all"))

# Scrollable frame configuration
scrollable_frame.bind(
    "<Configure>",
	lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

# Create the window inside the canvas
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

# Pack canvas and scrollbar
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Function to add messages
def add_message(text, sender):
    # Create a full-width container for the message
    container = ttk.Frame(scrollable_frame)
    container.pack(fill="x", padx=10, pady=5)

    # Stretch the container to match the width of the parent
    container.grid_columnconfigure(0, weight=1)

    if sender == "user":
        # User message (aligned right, within the full-width container)
        label = ttk.Label(
            container,
            text=text,
            wraplength=200,
            bootstyle="success-inverse",
            justify="right",
            padding=10
        )
        label.grid(row=0, column=1, sticky="e", padx=10)  # Align to the right
    elif sender == "ai":
        # AI message (aligned left, within the full-width container)
        label = ttk.Label(
            container,
            text=text,
            wraplength=200,
            bootstyle="primary-inverse",
            justify="left",
            padding=10
        )
        label.grid(row=0, column=0, sticky="w", padx=10)  # Align to the left

#default functions
def speak(text):
    if speaker_lang != 'uz':
        engine.say(text)
        engine.runAndWait()
    else:
        speak_uz(text)

def speak_uz(text):
    url = "https://api.muxlisa.uz/v1/api/services/tts/"
    speaker_id = "0"

    payload = f"token={muxlisa_token}&text={text}&speaker_id={speaker_id}"

    headers = {
		'Content-Type': 'application/x-www-form-urlencoded'
	}

    response = requests.request("POST", url, headers=headers, data=payload)

    with open("speaker_audio.ogg", "wb") as f:
        f.write(response.content)

    filename = "speaker_audio.ogg"
    playsound(filename)

def recognize_uz():
    url = "https://api.muxlisa.uz/v1/api/services/stt/"

    payload = {
		"token": muxlisa_token
	}
    files=[
		('audio',('query.wav',open('query.wav','rb'),'audio/wav'))
	]
    headers = {}

    response = requests.request("POST", url, headers=headers, data=payload, files=files)

    try:
        response_json = json.loads(response.text)
        text = response_json["message"]["result"]["text"]
        return text
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing response: {e}")
        return 'None'

def speak_phrase(phrase_key):
    if speaker_lang == 'en':
        speak(phrases[phrase_key][0])
    elif speaker_lang == 'ru':
        speak(phrases[phrase_key][1])
    elif speaker_lang == 'uz':
        speak(phrases[phrase_key][2])

def greeting():
	hour = int(datetime.datetime.now().hour)
	if hour>= 0 and hour<12:
		speak_phrase('morning')
		add_message(text=phrases['morning'][lang_idx], sender='ai')
	elif hour>= 12 and hour<16:
		speak_phrase('afternoon')
		add_message(text=phrases['afternoon'][lang_idx], sender='ai')
	elif hour>= 16 and hour<21:
		speak_phrase('evening')
		add_message(text=phrases['evening'][lang_idx], sender='ai')
	else:
		speak_phrase('night')
		add_message(text=phrases['night'][lang_idx], sender='ai')
	speak_phrase('greeting')

def takeCommand():
	global query
	r = sr.Recognizer()

	with sr.Microphone() as source:
		print("Listening...")
		r.pause_threshold = 1
		audio = r.listen(source)
	try:
		print("Recognizing...")
		if speaker_lang == 'en':
			query = r.recognize_google(audio, language ='en-in')
		elif speaker_lang == 'ru':
			query = r.recognize_google(audio, language = 'ru')
		elif speaker_lang == 'uz':
			with wave.open("query.wav", "wb") as wf:
				wf.setnchannels(1)  
				wf.setsampwidth(2)  # 16 bits per sample
				wf.setframerate(40000)  # 16 kHz sampling rate
				wf.writeframes(audio.get_raw_data())
			query = recognize_uz()
		print(f"User said: {query}\n")
	except Exception as e:
		print(e)
		print("Unable to Recognize your voice.")
		query = "None"

#command_helper_functions
def extract_number(number_words):
    global query
    # Split the query into words
    words = query.lower().split()
    # Initialize a list to store identified numbers
    identified_numbers = []
    # Iterate through each word in the query
    for word in words:
        # Check if the word exists in the number_words dictionary
        if word in number_words:
            # Add the corresponding number to the list
            identified_numbers.append(number_words[word])
    if 10 in identified_numbers:
        return sum(identified_numbers)
    else:
        try:
            return identified_numbers[0]
        except:
            return []

def is_cyrillic(text):
	return bool(re.search(r'[а-яА-ЯёЁ]', text))

def google_search():
    query = remove_keyword('open_website')
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({"q": query})

    headers = {
        'X-API-KEY': 'cec829226ea002f244486facb7943f554e34a3f2',  # Replace with your actual API key
        'Content-Type': 'application/json'
    }

    try:
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        # Extracting the first (best) search result link
        if "organic" in data and len(data["organic"]) > 0:
            webbrowser.open_new_tab(data["organic"][0]["link"])
            add_message(sender='ai', text=phrases['link_opened'][lang_idx])
            speak_phrase('link_opened')

    except Exception as e:
        add_message(sender='ai', text=phrases['search_fail'][lang_idx])
        speak_phrase('search_fail')

def adjust_volume(difference):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    )
    volume = interface.QueryInterface(IAudioEndpointVolume)

    current_volume = volume.GetMasterVolumeLevelScalar() * 100
    new_volume = max(0, current_volume + difference) / 100

    volume.SetMasterVolumeLevelScalar(new_volume, None)
    return new_volume * 100

#query correctors

def check_keyword(list):
    global query
    keyword_list = query_keywords[list]
    for i in range(0, len(keyword_list) - 1):
        keyword = keyword_list[i].lower()
        query = query.lower()
        if keyword in query:
            return True
    return False

def remove_keyword(substring_list):
	string = query
	substring_list = query_keywords[substring_list]
	string = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9]', ' ', string).lower()
	substring_list = [re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9]', ' ', substring_list[i]).lower() for i in range(0, len(substring_list) - 1)]
	for i in range(0, len(substring_list) - 1):
		string = string.replace(substring_list[i], '')
	return string

#command functions
def activate():
	speak_phrase('active')
	global assistant_active
	assistant_active = True

def deactivate():
	speak_phrase('deactivate')
	global assistant_active
	assistant_active = False

def type_keyboard():
	speak_phrase('typing')
	query = remove_keyword('type_keyboard')
	if query.startswith(' '):
		query = query[1:]
	print('Typing the following: ' + query)
	if is_cyrillic(query):
		pyperclip.copy(query)
		pyautogui.hotkey('ctrl', 'v')
	else:
		pyautogui.write(query, interval=0.1)

def remove_last_word():
    pyautogui.hotkey('ctrl', 'backspace')

# def wiki_search():
# 	speak_phrase('search_wiki')
# 	query = remove_keyword('wiki')
# 	print('Wiki search title: ' + query)
# 	wikipedia.set_lang(speaker_lang)
# 	try:
# 		results = wikipedia.summary(query, sentences = 2)
# 		if speaker_lang == 'uz':
# 			add_message(text='Vikipediya ma\'lumotlariga ko\'ra: ' + results, sender='ai')
# 			speak('Vikipediya ma\'lumotlariga ko\'ra: ' + results)
# 		elif speaker_lang == 'ru':
# 			add_message(text='Согласно данным из Википедии: ' + results, sender='ai')
# 			speak('Согласно данным из Википедии: ' + results)
# 		elif speaker_lang == 'en':
# 			add_message(text='According to information from Wikipedia: ' + results, sender='ai')
# 			speak('According to information from Wikipedia: ' + results)
# 	except wikipedia.exceptions.DisambiguationError:
# 		speak_phrase('wiki_specify')
# 	except wikipedia.exceptions.PageError:
# 		speak_phrase('wiki_search_fail')
# 	except:
# 		speak_phrase('error')

def get_weather():
    city = 'Tashkent'
    API_KEY = "445730664e1f4855b5e150633253001"
    BASE_URL = "http://api.weatherapi.com/v1/current.json"

    # try:
        # Make the request to WeatherAPI
    response = requests.get(BASE_URL, params={
        "key": API_KEY,
        "q": city,
        "aqi": "no",  # Disable air quality index
    })
    response.raise_for_status()  # Raise exception for HTTP errors
    data = response.json()

    # Extract weather information
    overall_state = data['current']['condition']['text']
    temperature = data['current']['temp_c']

    weather_info_en = f'Today the weather is {weather_state_translations[overall_state]}, the temperature is {temperature:.1f}'
    weather_info_ru = f'Сегодня погода {weather_state_translations[overall_state][1]}, температура {temperature:.1f}'
    weather_info_uz = f'Bugun havo {weather_state_translations[overall_state][0]}, temperatura {temperature:.1f}'

    # Print results
    print(f"The weather in {city} is currently '{overall_state}' with a temperature of {temperature:.1f}°C.")
    if speaker_lang == 'ru':
        add_message(weather_info_ru, sender='ai')
        speak(weather_info_ru)
    elif speaker_lang == 'en':
        add_message(text=weather_info_en, sender='ai')
        speak(weather_info_en)
    elif speaker_lang == 'uz':
        add_message(text=weather_info_uz, sender='ai')
        speak(weather_info_en)
    # except requests.exceptions.RequestException as e:
    #     print(f"Error fetching weather data: {e}")
    # except KeyError:
    #     print("Could not find weather data for the specified city.")

def tell_time():
	strTime = datetime.datetime.now().strftime("%H:%M")
	speak_phrase('time')
	speak(f"{strTime}")

def tell_date():
	date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    # Dictionaries for month and ordinal translations
	months = {
        "01": ["January", "Январь", "Yanvar"],
        "02": ["February", "Февраль", "Fevral"],
        "03": ["March", "Март", "Mart"],
        "04": ["April", "Апрель", "Aprel"],
        "05": ["May", "Май", "May"],
        "06": ["June", "Июнь", "Iyun"],
        "07": ["July", "Июль", "Iyul"],
        "08": ["August", "Август", "Avgust"],
        "09": ["September", "Сентябрь", "Sentabr"],
        "10": ["October", "Октябрь", "Oktabr"],
        "11": ["November", "Ноябрь", "Noyabr"],
        "12": ["December", "Декабрь", "Dekabr"]
    }
    
	ordinals = {
        "1": ["first", "первое", "birinchi"],
        "2": ["second", "второе", "ikkinchi"],
        "3": ["third", "третье", "uchinchi"],
        "4": ["fourth", "четвертое", "to'rtinchi"],
        "5": ["fifth", "пятое", "beshinchi"],
        "6": ["sixth", "шестое", "oltinchi"],
        "7": ["seventh", "седьмое", "yettinchi"],
        "8": ["eighth", "восьмое", "sakkizinchi"],
        "9": ["ninth", "девятое", "to'qqizinchi"],
        "10": ["tenth", "десятое", "o'ninchi"],
    }
    
    # Split the date string
	year, month, day = date_str.split("-")
	day = day.lstrip("0")  # Remove leading zeros
    
    # Get index for language

    # Construct readable date
	ordinal = ordinals.get(day, ["", "", ""])[lang_idx]
	month_name = months.get(month, ["", "", ""])[lang_idx]
	speak_phrase('date')
	if lang_idx == 0:
		speak(f"{ordinal} {month_name} of {year}")
	elif lang_idx == 1:
		speak(f"{ordinal.capitalize()} {month_name} {year}года")
	elif lang_idx == 2:
		speak(f"{ordinal.capitalize()} {month_name} {year}inchi yil")

def scroll():
    scroll_amount = 1000
    if check_keyword('up'):
        print('scrolling up')
        pyautogui.scroll(scroll_amount)
    if check_keyword('down'):
        print('scrolling down')
        pyautogui.scroll(-scroll_amount)

def change_lang():
	global speaker_lang
	if check_keyword('russian'):
		speaker_lang = 'ru'
		engine.setProperty('voice', voices[0].id)
	elif check_keyword('english'):
		speaker_lang = 'en'
		engine.setProperty('voice', voices[1].id)
	elif check_keyword('uzbek'):
		speaker_lang = 'uz'
	speak_phrase('change_lang')

def run_translator():
    pyautogui.typewrite('translate.google.com')
    time.sleep(0.2)
    pyautogui.press('enter')

def run_youtube():
    pyautogui.typewrite('youtube.com')
    time.sleep(0.2)
    pyautogui.press('enter')

def open_chrome():
	filepath = f"{drive_letter}\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
	os.startfile(filepath)
	time.sleep(0.3)
	pyautogui.hotkey('win', 'up')

def open_tg():
	filepath = f"{drive_letter}\\Users\\{current_user_name}\\AppData\\Roaming\\Telegram Desktop\\Telegram.exe"
	os.startfile(filepath)
	time.sleep(0.2)
	pyautogui.hotkey('win', 'up')

def open_calc():
	path = f"{drive_letter}\\Windows\\System32\\calc.exe"
	os.startfile(path)

def double_switch_windows():
	pyautogui.keyDown('alt')
	pyautogui.press('tab')
	time.sleep(0.2)
	pyautogui.press('tab')
	pyautogui.keyUp('alt')

def double_switch_tabs():
    pyautogui.keyUp('alt')
    pyautogui.keyDown('ctrl')
    pyautogui.press('tab')
    time.sleep(0.2)
    pyautogui.press('tab')
    pyautogui.keyUp('ctrl')

def switch_windows():
	pyautogui.hotkey('alt', 'tab')

def open_new_tab():
    pyautogui.hotkey('ctrl', 't')

def switch_tabs():
	pyautogui.hotkey('ctrl', 'tab')

def close_window():
	pyautogui.click(1900, 30)
 
def minimize_window():
	pyautogui.click(1800, 20)

def minimize_all_windows():
	pyautogui.hotkey('win', 'm')

def press_plus():
	pyautogui.press('+')

def press_multiply():
	pyautogui.press('*')

def press_minus():
	pyautogui.press('-')

def press_slash():
	pyautogui.press('/')

def brackets_open():
	pyautogui.press('(')

def brackets_close():
	pyautogui.press(')')

def quote():
	pyautogui.press('"')

def press_excl():
	pyautogui.press('!')

def press_qstn():
	pyautogui.press('?')

def press_colon():
	pyautogui.press(';')

def press_space():
	pyautogui.press(' ')

def press_equal():
	pyautogui.press('=')

def press_enter():
	pyautogui.press('enter')

def press_esc():
	pyautogui.press('esc')

def pause_media():
	pyautogui.press('pause')

def chat_control():
    chat_number = None
    if check_keyword('folder'):
        print('folder control')
        if check_keyword('up') and chat_folder_index > 1:
            print('folder up')
            chat_folder_index -= 1
            print(chat_folder_index)
            pyautogui.hotkey('ctrl', f"{chat_folder_index}")
        elif check_keyword('down'):
            print('folder down')
            chat_folder_index += 1
            print(chat_folder_index)
            pyautogui.hotkey('ctrl', f"{chat_folder_index}")
    else:
        if query.split(' ')[0] in list(number_words.keys()):
            chat_number = number_words[query.split(' ')[0]]
        elif check_keyword('lower_chat'):
            pyautogui.hotkey('alt', 'down')
        elif check_keyword('prev_chat'):
            pyautogui.hotkey('alt', 'up')
        else:
            try:
                chat_number = int(query.split(' ')[0].replace('th', ''))
            except:
                pass
        if chat_number is not None:
            pyautogui.press('esc')
            for i in range(0, chat_number):
                if check_keyword('up'):
                    pyautogui.press('up')
                else:
                    pyautogui.press('down')
                time.sleep(0.1)
            pyautogui.press('enter')

def who_ru():
	speak_phrase('who_ru')
	add_message(text=phrases['who_ru'][lang_idx], sender='ai')

def tell_about_yourself():
	speak_phrase('tell_about_yourself')

def play_yt():
    # global assistant_active
    query = remove_keyword('play')
    # assistant_active = False
    pywhatkit.playonyt(query)

def take_screenshot():
    pyautogui.hotkey('win', 'shift', 's')
    time.sleep(0.3)
    pyautogui.click(1000, 20)
    time.sleep(1)
    pyautogui.click(1875, 920)
    
def record_vm():
    record_btn_x, record_btn_y = 1895, 1020
    drag_x, drag_y = 1895, 720

    time.sleep(2)
    pyautogui.moveTo(record_btn_x, record_btn_y)
    pyautogui.mouseDown()
    time.sleep(0.5)
    pyautogui.moveTo(drag_x, drag_y, duration=0.2)
    pyautogui.mouseUp()
    time.sleep(5)
    record_btn_x, record_btn_y = 1895, 1020
    pyautogui.click(record_btn_x, record_btn_y)

def paste():
    pyautogui.hotkey('ctrl', 'v')

def copy():
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'c')

def turn_off():
	speak_phrase("shut_down")
	subprocess.call(["shutdown", "/s"])

def restart():
	speak_phrase("restart")
	subprocess.call(["shutdown", "/r"])

def just_pass():
    pass

def volume_up():
	speak_phrase('volume_up')
	adjust_volume(10)

def volume_down():
	speak_phrase('volume_down')
	adjust_volume(-10)

def gemini_search():
    global model
    query = remove_keyword('gemini')
    response = model.generate_content(query)
    answer = ' '.join(re.split(r'(?<=[.!?])\s+', response.text)[:3]).replace('*', '')
    add_message(text=answer, sender='ai')
    speak(answer)

def audio_call():
    pyautogui.click(1820, 50)
    time.sleep(0.2)
    pyautogui.click(1025, 745)

def video_call():
    pyautogui.click(1820, 50)
    time.sleep(0.2)
    pyautogui.click(890, 740)

#lists_dicionaries

weather_state_translations = {
    "Clear": ["Ochiq", "Ясная"],
    "Partly Cloudy": ["Qisman bulutli", "Переменная облачность"],
    "Cloudy": ["Bulutli", "Облачная"],
    "Overcast": ["Bulutli", "Пасмурная"],
    "Sunny": ["Quyoshli", "Солнечная"],
    "Patchy Rain": ["Yomg'irli", "Небольшой дождь"],
    "Light Rain": ["Yengil yomg'ir", "Слабый дождь"],
    "Moderate Rain": ["O'rtacha yomg'ir", "Умеренный дождь"],
    "Heavy Rain": ["Kuchli yomg'ir", "Сильный дождь"],
    "Very Heavy Rain": ["Juda kuchli yomg'ir", "Очень сильный дождь"],
    "Extreme Rain": ["Ekstremal yomg'ir", "Проливной дождь"],
    "Light Sleet": ["Yengil yomg'irli qor yog'ishi", "Легкий снег с дождем"],
    "Moderate Sleet": ["O'rtacha yomg'irli qor yog'ishi", "Умеренный снег с дождем"],
    "Heavy Sleet": ["Kuchli yomg'irli qor yog'ishi", "Сильный снег с дождем"],
    "Light Snow": ["Yengil qor", "Легкий снег"],
    "Moderate Snow": ["O'rtacha qor", "Умеренный снег"],
    "Heavy Snow": ["Kuchli qor", "Сильный снег"],
    "Very Heavy Snow": ["Juda kuchli qor", "Очень сильный снег"],
    "Extreme Snow": ["Ekstremal qor", "Проливной снег"],
    "Light Showers": ["Yengil jala", "Кратковременный дождь"],
    "Moderate Showers": ["O'rtacha jala", "Кратковременный умеренный дождь"],
    "Heavy Showers": ["Kuchli jala", "Кратковременный сильный дождь"],
    "Torrential Rain Shower": ["Kuchli jala", "Ливень"],
    "Light Freezing Rain": ["Muzlagan yomg'ir", "Легкий ледяной дождь"],
    "Moderate Freezing Rain": ["O'rtacha muzlagan yomg'ir", "Умеренный ледяной дождь"],
    "Heavy Freezing Rain": ["Kuchli muzlagan yomg'ir", "Сильный ледяной дождь"],
    "Light Ice Pellets": ["Mayda muz donalari", "Легкий град"],
    "Moderate Ice Pellets": ["O'rtacha muz donalari", "Умеренный град"],
    "Heavy Ice Pellets": ["Yirik muz donalari", "Сильный град"],
    "Snow": ["Qor", "Снежная"],
    "Blizzard": ["Bo'ron", "Метельная"],
    "Fog": ["Tuman", "Туманная"],
    "Mist": ["Tuman", "Дымка"],
    "Smoke": ["Tutun", "Дым"],
    "Haze": ["Chang", "Мгла"],
    "Sand/Dust Storms": ["Qum / chang bo'ronlari", "Песчаные/пыльные бури"],
}

number_words = {
	"one": 1,
	"two": 2,
	"three": 3,
	"four": 4,
	"five": 5,
	"six": 6,
	"seven": 7,
	"eight": 8,
	"nine": 9,
	"ten": 10,
	"eleven": 11,
	"twelve": 12,
	"thirteen": 13,
	"fourteen": 14,
	"fifteen": 15,
	"sixteen": 16,
	"first": 1,
	"second": 2,
	"third": 3,
	"fourth": 4,
	"fifth": 5,
	"sixth": 6,
	"seventh": 7,
	"eighth": 8,
	"ninth": 9,
	"tenth": 10,
	"eleventh": 11,
	"twelfth": 12,
	"thirteenth": 13,
	"fourteenth": 14,
	"fifteenth": 15,
	"sixteenth": 16,
	"один": 1,
	"два": 2,
	"три": 3,
	"четыре": 4,
	"пять": 5,
	"шесть": 6,
	"семь": 7,
	"восемь": 8,
	"девять": 9,
	"десять": 10,
	"одинадцать": 11,
	"двенадцать": 12,
	"тринадцать": 13,
	"четырнадцать": 14,
	"пятнадцать": 15,
	"шестнадцать": 16,
	"sixteenth": 16,
	"первый": 1,
	"второй": 2,
	"третий": 3,
	"четвертый": 4,
	"четвёртый": 4,
	"пятый": 5,
	"шестой": 6,
	"седьмой": 7,
	"восьмой": 8,
	"девятый": 9,
	"десятый": 10,
	"одинадцатый": 11,
	"двенадцатый": 12,
	"тринадцатый": 13,
	"четырнадцатый": 14,
	"пятнадцатый": 15,
	"шестнадцатый": 16,
	"первое": 1,
	"второе": 2,
	"третье": 3,
	"четвертое": 4,
	"четвёртое": 4,
	"пятое": 5,
	"шестое": 6,
	"седьмое": 7,
	"восьмое": 8,
	"девятое": 9,
	"десятое": 10,
	"одинадцатое": 11,
	"двенадцатое": 12,
	"тринадцатое": 13,
	"четырнадцатое": 14,
	"пятнадцатое": 15,
	"шестнадцатое": 16,
	"bir": 1,
	"ikki": 2,
	"uch": 3,
	"tort": 4,
	"besh": 5,
	"olti": 6,
	"yetti": 7,
	"sakkiz": 8,
	"to'qqiz": 9,
	"on": 10,
	"on bir": 11,
	"on ikki": 12,
	"on uch": 13,
	"on tort": 14,
	"on besh": 15,
	"on olti": 16,
	"birinchi": 1,
	"ikkinchi": 2,
	"uchinchi": 3,
	"tortinchi": 4,
	"beshinchi": 5,
	"oltinchi": 6,
	"yettinchi": 7,
	"sakkizinchi": 8,
	"to'qqizinchi": 9,
	"oninchi": 10,
	"on birinchi": 11,
	"on ikkinchi": 12,
	"on uchinchi": 13,
	"on tortinchi": 14,
	"on beshinchi": 15,
	"on oltinchi": 16
}

phrases = {
	"greeting": ['Welcome to System. How can I help you?', 'Добро пожаловать в систему. Как я могу вам помочь?', 'Tizimga xush kelibsiz. Sizga qanday yordam bera olaman?'],
	"morning": ['Good Morning !', 'Доброе утро !', 'Hayirli tong!'],
	"afternoon": ['Good Afternoon !', 'Добрый день !', 'Hayirli kun!'],
	"evening": ['Good Evening !', 'Добрый вечер !', 'Hayirli kech!'],
	"night": ['Good Night !', 'Доброй ночи !', 'Hayirli tun'],
	"search_wiki": ['Searching Wikipedia...', 'Поиск в Википедии...', 'Vikipediyadan qidirib koraman...'],
	"acc_wiki": ['According to Wikipedia...', 'Согласно Википедии...', 'Vikipedia malumotlari boyicha...'],
	"search_fail": ['Unfortunately, nothing was found from internet. Try to search something else', 'К сожалению, из Википедии ничего не нашлось, попробуйте поискать что-то другое', 
                      'Afsuski, Vikipediadan hech narsa topilmadi, iltimos boshqa narsa qidirib koring'],
	"search_specify": ['Try specifying what you mean and paraphrase your query', 'Постарайтесь задать вопрос по-конкретней или перефразируйте его', 
                  'Iltimos, aniqroq narsa qidirib koring'],
	"time": ['Current time is: ', 'Текущее время: ', 'Hozirgi vaqt: '],
	"date": ['Todays date is: ', 'Сегодняшняя дата: ', 'Bugungi sana: '],
	'change_lang': ['The language is switched', 'Язык переключен', 'Til ozgartirildi'],
	'active': ['Assistant is activated', 'Ассистент активирован', 'Assistent faollashtirildi'],
	'deactivate': ['Assistant is passive', 'Ассистент переключен в пассивный режим', 'Assistent passiv holatga otkazildi'],
	'typing': ['Typing this text...', 'Набираю этот текст...', 'Matn yozilmoqda'],
	'results_found': ['The following result is found...', 'Найден следующий результат...', 'Quidagi natija topildi...'],
	'no_results_found': ['No results are found...', 'Результов не найдено...', 'Hech qanday natija topilmadi'],
	'volume_up': ['Volume has been increased...', 'Звук увеличен...', 'Ovoz ko\'tarildi'],
	'volume_down': ['Volume has been decreased...', 'Звук уменьшен...', 'Ovoz pasaytirildi'],
	'who_ru': ['I am your vitual assisstant, Jamila', 'Я - ваш виртуальный ассистент Джамиля', 'Men - Jamila, sizning ovozli yordamchingizman'],
	'tell_about_yourself': ['My name is Jamila AI and I am your virtual assistant. This assistant was created in January of 2025 by students of Muhammad Al-Khwarizmi specialized school specifically to improve the computer control experience for people with disabilities.',
				'Меня зовут Джамиля AI и я ваш виртуальный ассистент. Этот ассистент был создан в Январе 2025го года учениками из специалезированной школы имени Мухаммада Аль-Хорезми специально для улучшения опыта управления компьютером для людей с ограниченными возможностями',
                'Mening ismim Jamila Ey Ay, men virtual assistentman.Ushbu assistent imkoniyati cheklangan insonlarning kompyuterni boshqarish faoliyatini yaxshilash uchun 2025-chi yilning Yanvar oyida Muhammad AL-Xorazmiy maktabi oquvchilari tomonidan yaratilgan'],
	'error': ['The query was unclear, please paraphrase it', 'Запрос не был ясным, пожалуйста перефразируйте его...', 'Sorov noaniq! Iltimos, qaytadan urunib koring'],
	'shut_down': ['Shutting down system...', 'Завершаю работу системы...', 'Tizim ochirilmoqda'],
	'restart': ['Restarting system...', 'Перезагружаю систему...', 'Tizim qayta ishga tushirilmoqda'],
    'lang_error': ['Sorry, it is unrecognized language', 'Простите, язык не распознан', 'Kechirasiz, til aniqlanmadi'],
    'link_opened': ['The following results are found:', 'Данные результаты нашлись:', "Quidagi natijalar topildi"],
}

query_keywords = {
	'activate': ['assistant activate', 'assistant active mode', 'assistant are you here', 'assistant you are here', 'assistant you here', 'assistant wake up', 'hello assistant', 
              'hi assistant', 'hey assistant', 'assistant where are you', 'ассистент активируйся', 'ассистент ты здесь', "ассистент ты где", "ассистент очнись", "ассистент привет",
              "привет ассистент", "эй ассистент", "ассистент очнись", "хэй асиистент", 'assistent faollash', 'assistent shu yerdamisan', 'assistentni faollashtirish', 
              'assistent aktiv holatga ot', 'assistent qanisan', 'assistent qayerdasan', 'assistent uygon', 'salom assistent', 'assistent salom', 'hey assistent', 'hoy assistent',
              activate],
	'deactivate': ['assistant deactivate', 'assistant stop', 'assistant pause', 'assistant sleep', 'assistant passive mode', 'ассистент досвидания', "ассистент до свидания", "ассистент стоп",
                "ассистент пауза", 'ассистент пассивный режим', 'ассистент режим пассивный', 'ассистент режим пассива',
                'assistent passiv holatga ot', 'assistent passiv', 'assistent passivlash', 'assistent pauza', 'assistent uxla', 'assistent toxta',
                deactivate],

	'change_lang_ru': ['измени язык', 'переключи язык', change_lang],
	'change_lang_en': ['change language', 'switch language', change_lang],
	'change_lang_uz': ['tilni ozgartir', 'tilni almashtir', change_lang],
 
	'uzbek': ['узекский', "uzbek", 'uz', just_pass],
	'russian': ['rus tili', 'ruscha', "russian", just_pass],
	'english': ['ingliz tili', 'inglizcha', 'anglizcha', "английский", just_pass],
 
	'gemini': ['from internet', 'according to wikipedia', "from wiki", "according to wiki", 'explain briefly', 'explain', 'tell me who', 'tell me', 'tell me what', 'explain me what',
          'explain me','из интернета', 'согласно интернету', 'who is', 'what is', 'согласно вики', 'из вики', "кто такой", "кто такая", "где находится", "кем является", "что такое",
          "объясни", "объясни в кратких словах", "поясни что такое", "поясни", "поясни вкратце", "в кратких словах", 'vikipediya malumotlariga kora', 'internetdagi malumotlariga tayanib',
          'internetdan olib aytchi', 'qisqacha tushuntirib ber', 'tushuntir', 'tushuntirib berchi', 'kimligini ayt', 'nimaligini ayt', 'u nima', 
          'oddiy qilib tushuntirib ber', 'oddiy tilda tushuntirib ber', 'manosi nima', 'ning manosi nima', 'dehqonchasiga tushuntirib ber', 'kim hisoblanadi', 'qayerda joylashgan', 
          'haqida nimalar bilasan', 'kim bolgan', 'kim', 'kim u', 'nima', 'nima u', 'ищем информации', 'поиск информации', 'найди информацию', 'поищи о', "найти информацию", "search about", 'find about', 'browse about', 'u haqida',
            'haqida qidir', 'haqida malumot', 'haqida izla', 'haqida izla', 'haqida internetdan qidir', 'haqida internetdagi malumotlar', 'haqida biror-bir malumot top',
          gemini_search],

    'open_website': ['open website', 'find website', 'найди вебсайт', 'найди сайт', "открыть сайт", "открой сайт",  "открыть вебсайт", "открой вебсайт", 'saytini top',
                    'saytini och', 'saytni och', 'saytni top', google_search],

	'type_keyboard': ['keyboard type', 'type on keyboard', 'набери на клавиатуре', "type text", 'набери текст', 'набрать текст', 'klaviaturada yoz', 'matnni ter', 'matnni yoz', type_keyboard],


	'play': ['play the song', 'play song', 'play from browser', 'play from you tube', 'play from youtube', 'play music', 'play the music', 'start music', "turn on", 'play video',
          'find video', 'find youtube video', 'find you tube video', 'включи',
          "включи музыку", 'qoshigini qoy', 'qoshigini top', 'ashulani top', 'qoshigini yutubdan qoy', 'qoshiqni youtube dan qoy', 'qoshiqni qoy',
          'qoshiqni you tube dan qoy', 'qoshigini ijro et', 'qoshiqni ijro et', 'videoni qoy', 'videoni top',
          play_yt],

	'pause': ['pause media', 'pause the media', 'play media', 'play the media', 'продолжай видео', "продолжай аудио", 'продолжать видео', "продолжать аудио", "стоп аудио", 
           "стоп видео", 'pauza', 'videoni toxtat', 'video stop', 'audio stop', 'davom ettir', 'davom et', 'davom etir', 'qoshiqni davom ettir',
           pause_media],

	'weather': ['what\'s the weather', 'weather outside', 'weather is', 'is it cold', 'is it warm', 'is it rainy', 'is it warm', 'do i need umbrella', 'should i take umbrella', 'should i take an umbrella', 
             'Какая погода', "погода прохладна", "на улице жарко", "на улице холодно", "на улице погода", "на улице прохладно", "мне надо взять зонт", "мне надо взять зонтик",
             "на улице зонт нужен", 'ob havo qanaqa', 'ob havo qanday', 'tashqarida havo', 'soyabon kerakmi', 'soyabon olishim kerakmi', 'kocha sovuqmi', 'kocha iliqmi', 'kocha issiqmi',
			 'kocha iliqmi', 'kochada havo', get_weather],

	'time': ['whats the time', 'what time it is', 'tell time', 'tell the time', "current time", 'какое время', "скажи время", "текущее время",
          'soat nechi', 'vaqtni ayt', 'soat necha boldi', 'soat necha', 'soat nechi boldi',
          tell_time],
	'date': ['whats the date', 'what date it is', 'tell date', 'tell the date', "current date", 'какая дата', "скажи дату", "текущая дата",
          'bugun sana', 'sana nechi', 'bugungi sana', 'sana necha',
          tell_date],

	'calc': ['i need to calculate', 'open calculator', 'run calculator', 'run the calculator', 'open the calculator', 'calculate', 'мне надо вычеслить', 'открой калькулятор', 
          'запусти калькулятор', 'открыть калькулятор', 'запустить калькулятор', 'вычесли', 'вычеслить', 'посчитай', 'посчитать', 'menga kalkulyator kerak', 'kalkulyatorni och',
          'kalkulyatorni ochish', 'hisobla', 'hisoblab yubor', 'hisoblachi', 'hisoblashim kerak',
          open_calc],
	'tg': ['open telegram', 'start telegram', "открой телеграм", "открой telegram", "запусти телеграм", "запусти telegram",
			'telegramni och', 'telegram ochilsin', 'telegram yoqilsin', 'telegramni yoq', 
			open_tg],
	'chrome': ['open chrome', 'start chrome', "открой хром", "запусти хром", 'open browser', 'start browser', "открой браузер", "запусти браузер", 'xromni och',
            'xrom ochilsin', 'brauzerni och', 'brauzer ochilsin', open_chrome],

	'switch_windows': ['switch windows', "switch the windows", "переключи приложения", "переключи приложение", "переключи окна", "переключить приложения",
                    "переключить окна", 'oynalarni almashtir', 'keyingi oyna', 'narigi oyna', 'keyingi oynani och', 'narigi oynani och', switch_windows],
	'double_switch_windows': ['double switch the tabs', 'double switch tabs', 'double switch windows', "double switch the windows", "дважды переключи приложения",
			"дважды переключи приложение", "дважды переключи окна", "дважды переключить приложения", "дважды переключить окна", 'oynalarni ikki marta almashtir', 
   			'oynalarni ikki marta ozgartir', double_switch_windows],

	'close_window': ['close the window', "close window", 'close the app', "close app", "закрой окно", "закрыть окно", "закрой приложение", "закрыть приложение", 'oynani yop', 'oyna yopilsin',
                  close_window],
	'minimize_window': ['minimize the window', "minimize the app",'minimize window', "minimize app", "сверни окно", "свернуть окно", "сверни приложение", "свернуть приложение", 
				'oyna kichraytirilsin', 'oynani kichraytir',
				minimize_window],
	'minimize_all_windows': ['minimize all the window', "minimize all the app",'minimize all windows', "minimize all apps", "сверни все окна", "свернуть все окна", "сверни все приложения",
				"свернуть все приложения", 'oynalarni yop', 'oynalar yopilsin', minimize_all_windows],

	'scroll': ['scroll', 'скролл', "scroll", "прокурти", "прокрутить", "прокрутка", 'скролл', "scroll", "прокрути", 
               "прокрутить", "прокрутка", 'skrol', 'skroll', 'skroll', 'skrol', scroll],

	'chat': ['chat', 'chad', 'chats', 'чат', "чатов", "чата", 'chat', 'chatga', 'chatlar', chat_control],
	'folder': ['folder', 'папка', 'papka', 'chatlar guruhi', just_pass],
	'prev_chat': ['upper chat', 'previous chat', 'чат выше', "на чат вверх", "на чат выше", 'bir chat tepaga', 'bitta chat tepaga', 'tepadagi chat', 'tepasidagi chat', just_pass],
	'lower_chat': ['lower chat', 'next chat', 'чат ниже', "на чат вниз", "на чат ниже", 'bir chat pastga', 'bitta chat pastga', 'pastdagi chat', 'pastidagi chat', just_pass],
	'down': ['down', 'вниз', 'past', 'pas', just_pass],
	'up': ['up', 'вверх', 'наверх', 'app', 'tepa', 'tepaga', 'teparoq', just_pass],

	'new_tab': ['open new tab', 'new tab', "open tab", "открой вкладку", "открой новую вкладку", 'открыть новую вкладку', 'открыть вкладку', 'открыть вкладку', 
            'yangi yorliq ochish', open_new_tab],
	'switch_tabs': ['switch tabs', "switch the tabs", "переключи вкладки", "переключить вкладки", 'keyingi yorliq', 'yorliqni almatshirish', switch_tabs],
	'double_switch_tabs': ['double switch tabs', "double switch the tabs", "дважды переключи вкладки", "дважды переключить вкладки", 'ikkita keyingi yorliq', 'ikki marta yorliqni almatshirish',
			double_switch_tabs],

	'remove_last_word': ['remove last word', 'remove the last word', 'cancel last word', 'cancel the last word', "убери последнее слово", 'убрать последнее слово', "удали последнее слово",
                      "удалить последнее слово", 'oxirgi sozni ochir', 'oxirgi sozni olib tashla', remove_last_word],
	'enter': ['enter', 'next line', 'ввод', "ввести", "следующая строка", 'энтэр', 'keyingi qator', 'enter', 'kiritish', press_enter],
	'plus': ['plus', 'add', 'плюс', 'добавить', 'qoshish', 'qoshamiz', 'qoshuv', press_plus],
	'multiply': ['times', 'multiply', 'умножить', 'kopaytirish', press_multiply],
	'slash': ['slash', 'devide', 'слэш', 'разделить', 'делить', 'делим', 'bolish', press_slash],
	'quote': ['quote', 'quotation starts', 'quotation open', 'кавычки', 'в кавычках', 'кавычки открываются', 'кавычки открыты', 'цитата', 'iqtibos', 'qoshtirnoq', quote],
	'brackets_open': ['brackets open', 'скобки открываются', 'скобки открыть', 'скобки открыты', 'скобки', 'qavs ochilsin', 'qavsni och', brackets_open],
	'brackets_close': ['brackets close', 'brackets closed', 'скобки закруваются', 'скобки закрыть', 'скобки закрыты', 'qavs yopilsin', 'qavsni yop', brackets_close],
	'excl': ['exclamation mark', 'восклицание', 'восклицательный знак', 'undov belgisi', 'undov', press_excl],
	'qstn': ['question mark', 'вопросительный знак', 'soroq beligisi', press_qstn],
	'equal': ['equals', 'equal', 'равно', 'равняется', 'teng', 'barobar', press_equal],
	'colon': ['colon', 'двоеточие', 'ikki nuqta', press_colon],
	'space': ['space', 'пробел', 'joy tashla', 'probel', press_space],
	'esc': ['esc', 'esk', 'ask', 'escape', 'эскейп', 'ескейп', 'эскей', 'ескей', 's key', 'eskeyp', press_esc],
	'minus': ['minus', 'dash', 'hyphens', 'substract', 'плюс', 'вычесть', 'отнять', 'ayiruv', 'ayiramiz', 'defiz', 'chiziqcha', 'chiziq', press_minus],
    'translator': ['translator', 'open translator', 'google translate', 'запустить переводчик', "запустить гугл переводчик", "открой переводчик", "открыть переводчик",
                   "зупусти переводчик", run_translator],
    'youtube': ['youtube', 'open youtube', 'let\'s watch some videos', 'run youtube', "запустить ютуб", "открой ютуб", "ютубчик",
                   "зупусти ютуб", 'yutubni och', 'youtube ni och', 'youtubeni och', 'you tube ni och', 'yu tube ni och', 'yu tub ni och', run_youtube],

	'volume_up': ['increase volume', 'volume up', 'увеличить звук', "усилить звук", "приумножить звук", "прибавить звук", "ovozni kotarish", "ovozni kopaytir", 'ovozni oshir',
               'ovozni kotar', "ovozini kotarish", "ovozini kopaytir", 'ovozini oshir', 'ovozini kotar', volume_up],
	'volume_down': ['decrease volume', 'volume down', 'снизить звук', "уменьшить звук", "понизить звук", "уменьши звук", "понизь звук", "ovozni pasaytirish", "ovozni pasaytir",
                 'ovozni pastla', "ovozini pasaytir", "ovozini pasaytirish", 'ovozini pastla', volume_down],

	'take_screenshot': ['take screenshot', 'take a screenshot', 'display screenshot', 'screenshot the display', 'сделай скриншот', "скриншот экрана", "скрин экрана", "сделать скриншот", "skrinshot qilish",
                    'skrinchot qilish', 'ekran skrinshot', 'ekran skrinchot', 'skrinshod', take_screenshot],
 
    'record_vm': ['start voice message', 'record voice message', 'voice message', 'запиши голосовое сообщение', 'записать голосовое сообщение', 'ovozli habar', 'ovozni yozib olish', 'ovozni yozish', record_vm],

	'turn_off': ['turn off system', 'shut down system', "отключи систему", "завершить работу системы", "заверши работу системы", 'tizimni ochirish', 'tizimni ochir', 
              'tizim ochirilsin', turn_off],
	'restart': ['restart system', 'перезагрузка системы', "перезагрузи систему", 'tizimni qayta ishga tushir', 'tizim qayta ishga tushirilsin', restart],

	'who_ru': ['who are you', 'who this is', 'кто это', "кто ты такой", "кто ты такая", "что ты такое", "что это такое", "sen kimsan", "kimsan sen", who_ru],
	'tell_about_yourself': ['who made you', 'who is your creator', 'who were you made by', "how were you born", "кто тебя создал", 'кто твой создатель', 'как ты появился',
			'tell about yourself', 'tell more about yourself', 'расскажи о себе', 'ozing haqingda gapirib ber', 'ozing haqingda batafsil gapirib ber', 'ushbu loyiha haqida gapirib ber',
			tell_about_yourself],
	'common_words': ['please', 'пожалуйста', "плиз", "плис", "ассистент", "assistent", "asistent", "yordamchi", 'iltimos', 'qila olasanmi', 'ilojisi bormi', 'iloji bormi', just_pass],
	'paste': ['paste', 'вставить', "вставка", 'qoyish', paste],
    'audio_call': ['audio call', 'call this contact', 'позвонить', "позвони этому контакту", "позвони ему", "позвони ей", "аудио звонок", audio_call],
    'audio_call': ['video call', 'call with camera', 'позвонить по видео', "позвонить с камерой", "видео звонок", video_call],
	'copy': ['copy', 'копировать', copy],
}

if __name__ == '__main__':
    def backgroundTasks():
        global query
        greeting()
        while True:
            takeCommand()
            query = query.lower()
            if query != 'none':
                query = query.replace('’', '')
                query = query.replace('\'', '')
                query = query.replace('`', '')
                query = query.replace('‘', '')
                add_message(text=query, sender='user')
                if check_keyword('activate'):
                    activate()
                elif check_keyword('deactivate'):
                    deactivate()
                else:
                    if assistant_active:
                        query = remove_keyword('common_words')
                        keyword_exists = False
                        for i in query_keywords:
                            if check_keyword(i):
                                query_keywords[i][-1]()
                                keyword_exists = True
                        if not keyword_exists:
                            number = extract_number(number_words)
                            if number != []:
                                keyword_exists = True
                                print('writing number')
                                pyautogui.write(str(number))
                            else:
                                pass
                        if not keyword_exists:
                            speak_phrase('error')
                        #     gemini_search()
            else:
                continue

    background_thread = threading.Thread(target=backgroundTasks)
    background_thread.start()
    
    root.bind("<Configure>", resize_canvas)
    root.mainloop()

    clear = lambda: os.system('cls')
    clear()
