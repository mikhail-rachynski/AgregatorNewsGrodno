import re
import exceptions

def cleaning_title(title):
    """Очиститель заголовков.
    Принимает заголовок с html-тегами и возвращает только текст
    """
    title = str(title)
    for items in exceptions.title:              
        title = re.sub(items[0], items[1], title)
    
    return title
            

def cleaning_content(text):
    """Очиститель текста.
    Принимает текст с html-тегами и возвращает только текст
    """
    text = ''.join(str(v) for v in text)
    for items in exceptions.content:              
        text = re.sub(items[0], items[1], text)

    return text