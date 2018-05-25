
from flask import Flask
from flask_login import  LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_moment import Moment
from flask_uploads import UploadSet, configure_uploads

from app.model import db, User, AnonymousUser
from config import configs

photos = UploadSet('PHOTO')
mail = None


def register_restful(app):
    pass


def register_extensions(app):
    db.init_app(app)
    Migrate(app, db)
    login_manager=LoginManager()
    login_manager.init_app(app)
    global mail
    mail=Mail(app)
    # mail.init_app(app)
    moment = Moment()
    moment.init_app(app)
    login_manager.anonymous_user = AnonymousUser
    @login_manager.user_loader
    def user_loader(id):
        return User.query.get(id)

    login_manager.login_view = 'auth.login'
    configure_uploads(app, photos)



def register_blueprints(app):
    from app.main import main
    app.register_blueprint(main)
    from app.auth import auth
    app.register_blueprint(auth)



def create_app(config):
    app = Flask(__name__)
    app.config.from_object(configs.get(config))
    register_restful(app)
    register_extensions(app)
    register_blueprints(app)
    return app