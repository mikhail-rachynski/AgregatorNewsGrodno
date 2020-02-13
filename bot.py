import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
import db
import configparser, math
import sp
import logging
import time
import flask



config = configparser.ConfigParser()
config.read(sp.path)

channel = config.get("Telegram", "Channel")
token = config.get("Telegram", "Token")
host = config.get("Telegram", "webhook")

API_TOKEN = token
# Хост и порт на которых запускается бот
WEBHOOK_HOST = host 
WEBHOOK_PORT = 443
# Адреса которые прослушивает Flask
WEBHOOK_LISTEN = '0.0.0.0'

WEBHOOK_SSL_CERT = '/home/pi/webhook_cert.pem'  # Path to the ssl certificate
WEBHOOK_SSL_PRIV = '/home/pi/webhook_pkey.pem'  # Path to the ssl private key

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (API_TOKEN)

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(API_TOKEN)

app = flask.Flask(__name__)


# Пустая страница если зайти на хост с ботом
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return ''



@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    """Обработка пришедших данных от телеграм
    """
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)


def send_news(news):
    """ Принимает ID новости из базы данных, получает её из базы данных
    отправляет в телеграм
    """
    try:
        # Получаем название сайта, заголовок и новость из базы данных
        site = news.site
        title = news.title
        current_news = news.news
        # Присваеваем экземпляр класса кнопок и передаём ID
        button = InlineButtons(news)
        # Форматируем заголовок и записываем в переменную title
        f_title = "*" + site + ":\n" + title + "*"
        # Количество символов для сообщений для отправки в канал
        message_length = 1200
        """Инструкця проверяет количество символов в исходной новости,
        и если она меньше message_length, то отправляет полное сообщение 
        в канал без кнопки "Читать полностью", а если новость больше
        message_length, то ограничевает длину и добавляет кнопку 
        "Читать полностью".
        """
        if len(current_news) < message_length:
            # Форматируем сообщение для отправки если новость маленькая
            formated_text = str(f_title) + "\n" + current_news
            # Отправка новости в канал с кнопками
            bot.send_message(channel, formated_text, parse_mode="Markdown", 
                    reply_markup=button.main_channel_small_news())
        else:
            # Форматируем сообщение для отправки если новость большая
            formated_text = str(f_title + "\n" + 
                    news
                    .news[0:message_length] + "...")
            # Отправка новости в канал с кнопками
            bot.send_message(channel, 
                    formated_text, 
                    parse_mode="Markdown", 
                    reply_markup=button.main_channel())

    except Exception as err:
        print("BOT ERROR: ", err)


class InlineButtons:  
    """ Класс кнопок под сообщением.
    Принимает объект новости
    """
    def __init__(self, news):
        self.url = news.url
        self.button = InlineKeyboardMarkup()
        self.read_all = InlineKeyboardButton(text='Читать полностью', 
                        callback_data=news.id)
        self.link_to_site = InlineKeyboardButton(text='Читать на сайте', 
                        url=news.url)

    def markup_decorator(func):
        """Декоратор для методов кнопок.
        """
        def wrapper(self, num_posts=0):
            """Декоратор для методов кнопокю
            """        
            self.button.row_width = 2
            func(self, num_posts)
            return self.button
        return wrapper

    @markup_decorator
    def main_channel(self, num_posts):
        """Метод добавляет кнопки "Читать полностью" и "Читать на сайте" 
        для новостей большого размера в канале.
        Возвращает декоратору "markup_decorator"
        """
        return self.button.add(self.read_all, self.link_to_site)
        
    @markup_decorator
    def main_channel_small_news(self, num_posts):
        """Метод добавляет кнопку "Читать на сайте" для новостей  
        маленького размера в канале.
        Возвращает декоратору "markup_decorator"
        """
        return self.button.add(self.link_to_site)
        
    @markup_decorator
    def del_messages_from_bot(self, num_posts):
        """Метод добавляет кнопку "Удалить" и "Читать на сайте" 
        для новостей присланных ботом пользователю.
        Возвращает декоратору "markup_decorator"
        """
        return self.button.add(InlineKeyboardButton(text='Удалить', 
                    callback_data="delete_" + str(num_posts)), 
                    self.link_to_site)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Функция ответных действий при нажатии кнопок.
    Принимает объект сообщения на котором произошло нажатие кнопки.
    call.data - строка переданная нажатой кнопкой
    """
    if call.data[0:6] == "delete":
        """Если срез строки содержит "delete", значи пришла команда на
        удаление сообщений. Строка имеет вид "delete_#", где
        # - количество сообщений для удаления.
        """
        if int(call.data[7:]) == 1:
            bot.delete_message(call.from_user.id, 
                    call.message.message_id)

        else:
            count = 0
            while count < int(call.data[7:]):
                bot.delete_message(call.from_user.id, 
                    (call.message.message_id - count))
                count += 1

    else:
        """Если в call.data строка с цифрами, значит была нажата кнопка 
        "Читать полностью", цифра это ID новости
        """
        # Записываем объект из быза данных в переменную
        news = db.request_news_by_id(call.data)       
        title = news.title
        text = news.news
        lenght_news = int(len(text))
        button = InlineButtons(news)

        if lenght_news < 4096:
            """ Отправка новости одним сообщением с кнопками от бота 
            пользователю, который нажал "Читать полностью" в канале.
            В методе "del_messages_from_bot" передаём аргумент "1", так 
            как сообщение одно.
            """
            bot.send_message(call.from_user.id, 
                    "*" + title + "*" + "\n" + text, 
                    parse_mode="Markdown",
                    reply_markup=button.del_messages_from_bot("1"))

        if lenght_news > 4096:
            """Разделение новости на равные части и отправка пользователю 
            который нажал "Читать полностью" в канале, если количество 
            символов в новости превышает 4096, с кнопками под последним
            сообщением. Разделённый текст помещается в список "cut_news",
            элементы которого отправляется ботом через цикл, передавая 
            методу "del_messages_from_bot" количество элементов списка.
            """            
            message_divider = math.ceil(lenght_news/3500)
            cut_news = []
            count = 1
            while count <= message_divider:
                cut_news.append(text[math.ceil(
                    (lenght_news/message_divider)*(count-1)):
                    math.ceil((lenght_news/message_divider)*count)])
                count += 1            
            
            for id, item in enumerate(cut_news):           
                if id == 0:
                    bot.send_message(call.from_user.id,
                        "*" + title + "*" + "\n" + item, 
                        parse_mode="Markdown")
                elif id == len(cut_news)-1:
                    bot.send_message(call.from_user.id, 
                        item, 
                        parse_mode="Markdown",
                        reply_markup=button.del_messages_from_bot
                        (num_posts=str(len(cut_news))))
                else:
                    bot.send_message(call.from_user.id, 
                        item, parse_mode="Markdown")


# Удаляет предыдущие параметры webhook
bot.remove_webhook()

time.sleep(0.1)

# Устанавливаем параметры webhook
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))


if __name__ == "__main__":
    app.run(host=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
            ssl_context=(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV),
            debug=True)         
               