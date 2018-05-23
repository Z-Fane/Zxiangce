import hashlib
from datetime import datetime

from flask import current_app, request
from flask_login import UserMixin, AnonymousUserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

db = SQLAlchemy()


class Permission:
    FOLLOW = 0x01  # 能关注的权限
    COMMENT = 0x02  # 能评论的权限
    CREATE_ALBUMS = 0x04  # 能创建相册权限
    MODERATE_COMMENTS = 0x08  # 管理其他用户的评论权限
    ADMINISTER = 0x80  # 管理员权限


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    default = db.Column(db.String(64), default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            # 用户
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.CREATE_ALBUMS, True),
            # 管理员
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.CREATE_ALBUMS |
                          Permission.MODERATE_COMMENTS, False),
            # 超级管理权限
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(username=r).first()
            if role is None:
                role = Role(username=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()


followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)
photo_like = db.Table(
    'photo_like',
    db.Column('photo_id', db.Integer, db.ForeignKey('photo.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)
album_like = db.Table(
    'album_like',
    db.Column('album_id', db.Integer, db.ForeignKey('album.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(64))
    url_s = db.Column(db.String(64))
    url_t = db.Column(db.String(64))
    about = db.Column(db.Text)

    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    order = db.Column(db.Integer)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    album_id = db.Column(db.Integer, db.ForeignKey('album.id'))
    user_like = db.relationship('User', secondary=photo_like,
                                backref=db.backref('photos_like', lazy='dynamic'),
                                lazy='dynamic',passive_deletes=True)
    comments = db.relationship('Comment', backref='photo', lazy='dynamic')

    def is_liked_by(self, user):
        return user in self.user_like



class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    about = db.Column(db.Text)
    cover = db.Column(db.String(64))
    type = db.Column(db.Integer, default=0)
    tag = db.Column(db.String(64))
    no_public = db.Column(db.Boolean, default=True)
    no_comment = db.Column(db.Boolean, default=True)
    asc_order = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    photos = db.relationship('Photo', backref='album', lazy='dynamic'
                             ,cascade='all, delete-orphan')
    album_like = db.relationship('User', secondary=album_like,
                                 backref=db.backref('album_like', lazy='dynamic'),
                                 lazy='dynamic',passive_deletes=True)
    def is_liked_by(self, user):
        return user in self.users


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    # body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    confirmed = db.Column(db.Boolean, default=False)
    location = db.Column(db.String(64))
    website = db.Column(db.String(64))
    background = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    like_public = db.Column(db.Boolean, default=True)
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    # 相册,一对多
    albums = db.relationship('Album', backref='author', lazy='dynamic')
    # 照片,一对多
    photos = db.relationship('Photo', backref='author', lazy='dynamic')
    # 评论 一对多
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    # 我喜欢的照片
    photo_likes = db.relationship('Photo', secondary=photo_like,
                                  backref=db.backref('users', lazy='dynamic'),
                                  lazy='dynamic')
    # 我喜欢的相册
    album_likes = db.relationship('Album', secondary=album_like,
                                  backref=db.backref('users', lazy='dynamic'),
                                  lazy='dynamic')
    # followers 粉丝
    # 我关注的人
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['ZXIANGCE_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://secure.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def can(self, permissions):
        return self.role is not None and \
               (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        id=str(self.id)
        return s.dumps({'confirm':self.id})



    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def is_like_photo(self, photo):
        return photo in self.photo_likes.all()

    def like_photo(self, photo):
        self.photo_likes.append(photo)

    def unlike_photo(self, photo):
        self.photo_likes.remove(photo)

    def is_like_album(self, album):
        return album in self.album_likes.all()

    def like_album(self, album):
        self.album_likes.append(album)

    def unlike_album(self, album):
        self.album_likes.remove(album)

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def generate_reset_token(self,expiration=3600):
        s=Serializer(current_app.config['SECRET_KEY'],expiration)
        return s.dumps({'reset_password':self.id})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


def __repr__(self):
    return '<Role %r>' % self.name
