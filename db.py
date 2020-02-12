import psycopg2
from sqlalchemy import create_engine
from sqlalchemy import Column, String, Integer, VARCHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import sessionmaker
import configparser
import sp


config = configparser.ConfigParser()
config.read(sp.path)

db_user = config.get("DataBase", "User")
db_password = config.get("DataBase", "Password")
db_name = config.get("DataBase", "DB_name")
db_host = config.get("DataBase", "Host")

# Подключаемся к базе данных PostgreSQL
engine = create_engine(f'postgresql+psycopg2://{db_user}:{db_password}@/{db_name}?host={db_host}', echo=False)
base = declarative_base()
session = sessionmaker(bind=engine)()        

class News(base):
    """Объект таблицы базы данных "news"."""
    __tablename__ = 'news'
    id = Column(Integer, primary_key=True)
    site = Column(VARCHAR)
    title = Column(VARCHAR)
    news = Column(VARCHAR)
    media = Column(VARCHAR)
    url = Column(VARCHAR)

    def __repr__(self):
        return "<News('{}, {}, {}, {}, {}')>".format(
                            self.site,
                            self.title,
                            self.news,
                            self.media,
                            self.url)                           

# Создание всех таблиц
base.metadata.drop_all(engine)
base.metadata.create_all(engine)



def send_news_to_database(data):
    """Запись в базу данных."""    
    news_data = News(site=f"{data[0]}", title=f"{data[1]}", news=f"{data[2]}", media=f"{data[3]}", url=f"{data[4]}")
    session.add(news_data)
    session.new
    session.commit()
    return news_data

def request_news_by_url(url):
    """ Чтение из базы данных по URL-адресу.
    Если запись отсутствует, то возвращает "None".
    """
    try:
        return session.query(News).filter_by(url=url).first()
    except:
        return None

def request_news_by_id(id):
    """ Чтение из базы данных по ID.
    Если запись отсутствует, то возвращает "None".
    """
    try:
        return session.query(News).filter_by(id=id).first()
    except:
        return None
       