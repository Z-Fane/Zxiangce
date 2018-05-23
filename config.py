import os

from flask_uploads import IMAGES


class BaseConfig(object):
    """ 配置基类 """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'very hard to guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_COMMIT_TEARDOWN = True

    ZXIANGCE_ADMIN = 'admin@zfane.cn'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    ZXIANGCE_MAIL_SUBJECT_PREFIX = u'[Z相册]'

    MAIL_SERVER='smtp.qq.com'
    MAIL_PORT=465
    MAIL_USE_SSL=True
    MAIL_USE_TLS=False
    MAIL_USERNAME='zfane@foxmail.com'
    MAIL_PASSWORD='rvutnscagytrbiag'
    MAIL_DEBUG = True

    MAIL_DEFAULT_SENDER='zfane@foxmail.com'

    UPLOADED_PHOTO_DEST = os.getcwd() + '/app/static/img/'
    UPLOADED_PHOTO_ALLOW = IMAGES


    ZXIANGCE_COMMENTS_PER_PAGE = 15
    ZXIANGCE_ALBUMS_PER_PAGE = 12
    ZXIANGCE_PHOTOS_PER_PAGE = 20
    ZXIANGCE_ALBUM_LIKES_PER_PAGE = 12
    ZXIANGCE_PHOTO_LIKES_PER_PAGE = 20
    ZXIANGCE_FOLLOWERS_PER_PAGE = 10


class DevelopmentConfig(BaseConfig):
    """ 开发环境配置 """
    DEBUG = True

    SQLALCHEMY_DATABASE_URI = 'mysql://root:zfane@localhost:3306/zxiangce?charset=utf8'


class ProductionConfig(BaseConfig):
    """ 生产环境配置 """
    pass


class TestingConfig(BaseConfig):
    """ 测试环境配置 """
    pass


configs = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}