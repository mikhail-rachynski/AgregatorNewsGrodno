import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
import db
import configparser, math
import sp


config = configparser.ConfigParser()
config.read(sp.path)

token = config.get("Telegram", "Token")
channel = config.get("Telegram", "Channel")


bot = telebot.TeleBot(token)


class InlineButtons:  
    """ Класс кнопок под сообщением.
    Принимает ID новости
    """
    def __init__(self, news_id):
        self.id = news_id
        self.url = db.request_news_by_id(news_id).url
        self.button = InlineKeyboardMarkup()
        self.read_all = InlineKeyboardButton(text='Читать полностью', 
                        callback_data=self.id)
        self.link_to_site = InlineKeyboardButton(text='Читать на сайте', 
                        url=self.url)

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


def send_news(news_id):
    """ Принимает ID новости из базы данных, получает её из базы данных
    отправляет в телеграм
    """
    try:
        # Получаем название сайта, заголовок и новость из базы данных
        site = db.request_news_by_id(news_id).site
        title = db.request_news_by_id(news_id).title
        current_news = db.request_news_by_id(news_id).news
        # Присваеваем экземпляр класса кнопок и передаём ID
        button = InlineButtons(news_id)
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
            formated_text = str(f_title + "\n" + db.request_news_by_id
                                                    (news_id).news)
            # Отправка новости в канал с кнопками
            bot.send_message(channel, 
                    formated_text, 
                    parse_mode="Markdown", 
                    reply_markup=button.main_channel_small_news())
        else:
            # Форматируем сообщение для отправки если новость большая
            formated_text = str(f_title + "\n" + 
                    db.request_news_by_id(news_id)
                    .news[0:message_length] + "...")
            # Отправка новости в канал с кнопками
            bot.send_message(channel, 
                    formated_text, 
                    parse_mode="Markdown", 
                    reply_markup=button.main_channel())

    except Exception as err:
        print("BOT ERROR: ", err)


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
        news_title = str(db.request_news_by_id(call.data).title)
        news_text = str(db.request_news_by_id(call.data).news)
        lenght_news = int(len(news_text))
        button = InlineButtons(call.data)

        if lenght_news < 4096:
            """ Отправка новости одним сообщением с кнопками от бота 
            пользователю, который нажал "Читать полностью" в канале.
            В методе "del_messages_from_bot" передаём аргумент "1", так 
            как сообщение одно.
            """
            bot.send_message(call.from_user.id, 
                    "*" + news_title + "*" + "\n" + news_text, 
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
                cut_news.append(news_text[math.ceil(
                    (lenght_news/message_divider)*(count-1)):
                    math.ceil((lenght_news/message_divider)*count)])
                count += 1            
            
            for id, item in enumerate(cut_news):           
                if id == 0:
                    bot.send_message(call.from_user.id,
                        "*" + news_title + "*" + "\n" + item, 
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
            